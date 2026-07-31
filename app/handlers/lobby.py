from typing import Callable

from aiogram import Bot, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.admin import AdminFilter
from app.filters.buttons import ReplyButtonFilter
from app.filters.state import BotStates
from app.utils import method_executor_msg, send_all_info
from database.clients.game import GameClient
from database.clients.user import UserClient
from database.schemas import AdminDto, GameDto, GameStatus, PlanetDto, PlayerDto
from keyboards import keyboards as kb
from messages import messager
from presets.pack import packs
from storage.clients.actions import ActionsClient
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
        messager.choose_pack(),
        reply_markup=kb.pack_keyboard()
    )
    await state.set_state(BotStates.choose_pack)


@lobby_router.callback_query(BotStates.choose_pack)
async def set_pack(
    call: types.CallbackQuery,
    state: FSMContext
):
    pack_name = call.data
    call.answer()
    await call.message.answer(
        messager.choose_number_of_planets(),
        reply_markup=kb.number_of_planets_keyboard(pack_name),
    )
    await state.set_state(BotStates.planets_numbers)


@lobby_router.callback_query(BotStates.planets_numbers)
async def set_number_of_planets(
    call: types.CallbackQuery,
    state: FSMContext,
    game_client: GameClient,
    session: AsyncSession,
):
    number, pack_name = call.data.split(',')
    number = int(number)
    for p in packs:
        if p.name == pack_name:
            pack = p
            break
    game = await game_client.create_game(
        session,
        admin_id=call.from_user.id,
        pack=pack,
        number_of_planets=number
    )
    call.answer()
    await call.message.answer(
        messager.game_created(game.id, number),
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
    session: AsyncSession,
):
    is_admin = await user_client.is_user_admin(session, message.from_user.id)
    if not is_admin:
        await user_client.make_new_user_if_not_exists(session, message.from_user.id)
    all_games = await game_client.get_all_games(session)
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


async def notify_lobby_on_join_leave(
    bot: Bot,
    game: GameDto,
    planet: PlanetDto,
    game_client: GameClient,
    session: AsyncSession,
    message: Callable[[str, int, int], str]
):
    active_players = await game_client.get_all_active_players(session, game.id)
    active_admins = await game_client.get_all_active_admins(session, game.id)

    for ouser in active_admins + active_players:
        await bot.send_message(
            ouser.tg_id,
            message(
                planet.name, len(active_players), game.num_planets
            ),
        )


@lobby_router.message(ReplyButtonFilter('Выйти из лобби'))
async def leave_lobby(
    message: types.Message,
    user_client: UserClient,
    game_client: GameClient,
    messages_client: MessagesClient,
    session: AsyncSession,
):
    tg_id = message.from_user.id
    user = await user_client.get_user(session, tg_id)
    game_id = user.game_id
    res = await method_executor_msg(
        message.bot,
        user_client.kick_user,
        tg_id,
        session, tg_id,
    )
    if not res:
        return
        
    await message.answer(
        messager.leaving_msg(),
        reply_markup=kb.start_keyboard(isinstance(user, AdminDto))
    )

    if isinstance(user, AdminDto):
        return
    
    message_ids = messages_client.find_all_messages(tg_id)
    if len(message_ids) > 0:
        await message.bot.delete_messages(tg_id, message_ids)
    messages_client.delete_all_messages(tg_id)
    game: GameDto = await user_client.get_game(session, game_id)
    
    if game.status != GameStatus.WAITING:
        return
    
    planet = await game_client.get_player_planet(session, tg_id, game.id)
    await notify_lobby_on_join_leave(
        message.bot, game, planet,
        game_client, session,
        messager.leave_for_others
    )


@lobby_router.callback_query(BotStates.choose_lobby_admin)
async def chosen_lobby_admin(
    call: types.CallbackQuery,
    state: FSMContext,
    user_client: UserClient,
    session: AsyncSession,
):
    gamecode = int(call.data)
    tgid = call.from_user.id
    game: GameDto = await user_client.get_game(session, gamecode)
    res = await method_executor_msg(
        call.bot,
        user_client.join_user,
        tgid,
        session, tgid, game.id
    )
    if not res:
        return
    await call.message.answer(
        messager.success_admin_enter(game.id),
        reply_markup=kb.ingame_keyboard(True),
    )
    await state.clear()


@lobby_router.callback_query(BotStates.choose_lobby)
async def chosen_lobby(
    call: types.CallbackQuery,
    state: FSMContext,
    user_client: UserClient,
    game_client: GameClient,
    actions_client: ActionsClient,
    messages_client: MessagesClient,
    session: AsyncSession,
):
    gamecode = int(call.data)
    tg_id = call.from_user.id
    game: GameDto = await game_client.get_game(session, gamecode)
    res = await method_executor_msg(
        call.bot,
        user_client.join_user,
        tg_id,
        session, tg_id, game.id
    )
    if not res:
        return
    planet = await game_client.get_player_planet(session, tg_id, game.id)
    await call.message.answer(
        messager.success_enter(game.id, planet.name),
        reply_markup=kb.ingame_keyboard(False),
    )
    if game.status == GameStatus.WAITING:
        await notify_lobby_on_join_leave(
            call.bot, game, planet,
            game_client, session,
            messager.success_enter_for_others
        )
    elif game.status == GameStatus.ROUND:
        planets: list[PlanetDto] = await game_client.get_all_planets_in_game(session, game.id, False)
        all_planets_and_cities = dict()
        for pl in planets:
            planet_cities = await game_client.get_cities_of_planet(
                session, pl.id,
                False, False
            )
            all_planets_and_cities[pl.id] = (pl, planet_cities)
        order_info = actions_client.get_order_info(planet.id)
        await send_all_info(
            bot=call.bot,
            game=game,
            planets_and_cities=all_planets_and_cities,
            planet_id=planet.id,
            order_info=order_info,
            user_id=tg_id,
            messages_client=messages_client,
        )
    await state.clear()

