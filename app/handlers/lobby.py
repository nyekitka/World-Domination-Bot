from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.filters.admin import AdminFilter
from app.filters.buttons import ReplyButtonFilter
from app.filters.state import BotStates
from app.utils import method_executor_msg
from database.clients.game import GameClient
from database.clients.user import UserClient
from database.schemas import GameDto, GameStatus, PlanetDto, PlayerDto
import keyboards as kb
from messages import messager
from presets.pack import packs
from storage.clients.messages import MessagesClient


lobby_router = Router()


@lobby_router.message(
    ReplyButtonFilter('Создать лобби'),
    AdminFilter()
)
async def create_game(
    message: types.Message,
    state: FSMContext
):
    await message.answer(
        'Выберите набор планет и городов для игры',
        reply_markup=kb.pack_keyboard()
    )
    await state.set_state(BotStates.choose_pack)


@lobby_router.callback_query(BotStates.choose_pack)
async def set_pack(
    call: types.CallbackQuery,
    state: FSMContext
):
    pack_name = call.data
    for p in packs:
        if p.name == pack_name:
            pack = p
            break
    await call.answer()
    await call.message.answer(
        messager.choose_number_of_planets(),
        reply_markup=kb.number_of_planets_keyboard(pack),
    )
    await state.set_state(BotStates.planets_numbers)


@lobby_router.callback_query(BotStates.planets_numbers)
async def set_number_of_planets(
    call: types.CallbackQuery,
    state: FSMContext,
    game_client: GameClient,
):
    number, pack_name = call.data.split(',')
    number = int(number)
    for p in packs:
        if p.name == pack_name:
            pack = p
            break
    game = await game_client.create_game(
        admin_id=call.from_user.id,
        pack=pack,
        number_of_planets=number
    )
    await call.answer()
    await call.message.answer(
        text=messager.game_created(game.id, number),
        reply_markup=kb.start_keyboard(True),
    )
    await state.clear()


@lobby_router.message(
    ReplyButtonFilter('Войти в лобби')
)
async def enter_game_player(
    message: types.Message,
    state: FSMContext,
    game_client: GameClient,
    user_client: UserClient,
):
    is_admin = await user_client.is_admin(message.from_user.id)
    if not is_admin:
        await user_client.make_new_user_if_not_exists(message.from_user.id)
    all_games = await game_client.get_all_games()
    if len(all_games) == 0:
        await message.answer(messager.no_games(), reply_markup=kb.start_keyboard(is_admin))
        return
    if is_admin:
        await state.set_state(BotStates.choose_lobby_admin)
    else:
        await state.set_state(BotStates.choose_lobby)
    await message.answer(
        messager.choose_lobby(), reply_markup=kb.choose_lobby_keyboard(all_games)
    )


@lobby_router.message(ReplyButtonFilter('Выйти из игры'))
async def leave_lobby(
    message: types.Message,
    user_client: UserClient,
    game_client: GameClient,
    redis_messages_client: MessagesClient,
):
    user = await user_client.get_user(message.from_user.id)
    res = await method_executor_msg(
        message.bot,
        user_client.kick_user,
        user.tg_id,
        user.tg_id,
    )
    if not res:
        return
    if isinstance(user, PlayerDto):
        await message.answer(
            messager.leaving_msg(),
            reply_markup=kb.start_keyboard(False)
        )
        message_ids = redis_messages_client.find_all_messages(user.tg_id)
        if len(message_ids) > 0:
            await message.bot.delete_messages(user.tg_id, message_ids)
        redis_messages_client.delete_all_messages(user.tg_id)
        game: GameDto = await user_client.get_game(user.game_id)
        if game.status == GameStatus.WAITING:
            active_players = await game_client.get_all_active_players()
            active_admins = await game_client.get_all_active_admins()
            planet: PlanetDto = await user_client.get_player_planet(user.id, game.id)
            for ouser in active_admins + active_players:
                await message.bot.send_message(
                    ouser.id,
                    messager.leave_for_others(
                        planet.name, len(active_players), game.num_planets
                    ),
                )
    else:
        await message.answer(
            messager.leaving_msg(),
            reply_markup=kb.start_keyboard(True)
        )


@lobby_router.callback_query(BotStates.choose_lobby_admin)
async def chosen_lobby_admin(
    call: types.CallbackQuery,
    state: FSMContext,
    user_client: UserClient,
    game_client: GameClient,
):
    gamecode = int(call.data)
    tgid = call.from_user.id
    game: GameDto = await game_client.get_game(gamecode)
    res = await method_executor_msg(
        call.bot,
        user_client.join_user,
        tgid,
        tgid, game.id
    )
    if not res:
        return
    await call.message.answer(
        messager.success_admin_enter(gamecode),
        reply_markup=kb.ingame_keyboard(True),
    )
    await state.clear()


# @lobby_router.callback_query(BotStates.choose_lobby)
# async def chosen_lobby(
#     call: types.CallbackQuery,
#     state: FSMContext,
#     user_client: UserClient,
#     game_client: GameClient,
#     messager: Messager,
# ):
#     gamecode = int(call.data)
#     tgid = call.from_user.id
#     game: GameDto = await game_client.get_game(gamecode)
#     res = await method_executor_msg(
#         call.bot,
#         user_client.join_user,
#         tgid,
#         tgid, game.id
#     )
#     if not res:
#         return
#     planet = await game_client.get_player_planet(tgid, game.id)
#     await call.message.answer(
#         messager.success_enter(gamecode, planet.name()),
#         reply_markup=kb.ingame_keyboard(False),
#     )
#     if game.status == GameStatus.WAITING:
#         active_players = await game_client.get_all_active_players(game.id)
#         active_admins = await game_client.get_all_active_admins(game.id)
#         for player in active_players:
#             await call.bot.send_message(
#                 player.tg_id,
#                 messager.success_enter_for_others(
#                     planet.name, len(active_players), game.num_planets
#                 ),
#             )
#         for admin in active_admins:
#             await call.bot.send_message(
#                 admin.tg_id,
#                 messager.success_enter_for_others(
#                     planet.name, len(active_players), game.num_planets
#                 ),
#             )
#     elif game.status == GameStatus.ROUND:
#         await print_all_info(game.round, planet, tgid)
#     await state.clear()