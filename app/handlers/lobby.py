from functools import partial
import logging
from typing import Callable


from aiogram import Bot, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.admin import AdminFilter
from app.filters.buttons import ReplyButtonFilter
from app.filters.state import BotStates
from app.utils import method_executor_call, method_executor_msg, send_all_info
from database.clients.game import GameClient
from database.clients.user import UserClient
from database.schemas import AdminDto, GameDto, GameStatus, PlanetDto, PlayerDto
from keyboards import keyboards as kb
from messages.renderer import MessageRenderer
from presets.pack import packs
from storage.clients.actions import ActionsClient
from storage.clients.messages import MessagesClient


lobby_router = Router()
logger = logging.getLogger(__name__)

@lobby_router.message(
    ReplyButtonFilter('Создать лобби'),
    AdminFilter()
)
async def create_game(
    message: types.Message,
    state: FSMContext,
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.create_game: Admin id=%s is creating a new game',
        message.from_user.id
    )
    await message.answer(
        **renderer.render('choose_pack'),
        reply_markup=kb.pack_keyboard()
    )
    await state.set_state(BotStates.choose_pack)


@lobby_router.callback_query(BotStates.choose_pack)
async def set_pack(
    call: types.CallbackQuery,
    state: FSMContext,
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.set_pack: Admin id=%s is setting pack for new game',
        call.from_user.id
    )
    pack_name = call.data
    await call.answer()
    await call.message.answer(
        **renderer.render('choose_pack'),
        reply_markup=kb.number_of_planets_keyboard(pack_name),
    )
    await state.set_state(BotStates.planets_numbers)


@lobby_router.callback_query(BotStates.planets_numbers)
async def set_number_of_planets(
    call: types.CallbackQuery,
    state: FSMContext,
    game_client: GameClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.set_number_of_planets: Admin id=%s is setting number of planets for new game',
        call.from_user.id
    )
    await call.answer()
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
    await call.answer()
    await call.message.answer(
        **renderer.render('on_game_created', game=game),
        reply_markup=kb.ingame_keyboard(True),
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
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.enter_game_player: User id=%s is entering a game',
        message.from_user.id
    )
    user = await user_client.make_new_user_if_not_exists(session, message.from_user.id, False)
    is_admin = isinstance(user, AdminDto)
    if user.game_id is not None:
        await message.answer(
            **renderer.render('already_in_game'),
            reply_markup=kb.ingame_keyboard(is_admin)
        )
        return
    all_games = await game_client.get_all_games(session)
    if len(all_games) == 0:
        await message.answer(
            **renderer.render('no_games_available'),
            reply_markup=kb.start_keyboard(is_admin),
        )
        return
    if is_admin:
        await state.set_state(BotStates.choose_lobby_admin)
    else:
        await state.set_state(BotStates.choose_lobby)
    await message.answer(
        **renderer.render('on_choose_lobby'),
        reply_markup=kb.choose_lobby_keyboard(all_games),
    )


async def notify_lobby_on_join_leave(
    bot: Bot,
    game: GameDto,
    planet: PlanetDto,
    game_client: GameClient,
    session: AsyncSession,
    message: Callable[..., dict[str, str | None]],
):
    active_players = await game_client.get_all_active_players(session, game.id)
    active_admins = await game_client.get_all_active_admins(session, game.id)

    for ouser in active_admins + active_players:
        await bot.send_message(
            ouser.tg_id,
            **message(
                planet=planet,
                game=game,
                current_players=len(active_players), 
            ),
        )


@lobby_router.message(ReplyButtonFilter('Выйти из лобби'))
async def leave_lobby(
    message: types.Message,
    user_client: UserClient,
    game_client: GameClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.leave_lobby: User id=%s is leaving a lobby',
        message.from_user.id
    )
    tg_id = message.from_user.id
    user = await user_client.get_user(session, tg_id)
    game_id = user.game_id
    planet = await game_client.get_player_planet(session, tg_id, game_id, False)
    res = await method_executor_msg(
        message.bot,
        user_client.kick_user,
        tg_id, renderer,
        session, tg_id,
    )
    if not res:
        return
        
    await message.answer(
        **renderer.render('on_leave_lobby'),
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
    
    await notify_lobby_on_join_leave(
        message.bot, game, planet,
        game_client, session,
        partial(renderer.render, key='player_leave_notification'),
    )


@lobby_router.callback_query(BotStates.choose_lobby_admin)
async def chosen_lobby_admin(
    call: types.CallbackQuery,
    state: FSMContext,
    user_client: UserClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.chosen_lobby_admin: Admin id=%s is choosing a lobby to enter',
        call.from_user.id
    )
    gamecode = int(call.data)
    tgid = call.from_user.id
    game: GameDto = await user_client.get_game(session, gamecode)
    res = await method_executor_call(
        user_client.join_user,
        call, renderer,
        session, tgid, game.id
    )
    if not res:
        return
    await call.message.answer(
        **renderer.render('on_success_enter_admin', game=game),
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
    renderer: MessageRenderer,
):
    logger.info(
        'lobby_router.chosen_lobby: Player id=%s is choosing a lobby to enter',
        call.from_user.id
    )
    gamecode = int(call.data)
    tg_id = call.from_user.id
    game: GameDto = await game_client.get_game(session, gamecode)
    res = await method_executor_call(
        user_client.join_user,
        call, renderer,
        session, tg_id, game.id
    )
    if not res:
        return
    planet = await game_client.get_player_planet(session, tg_id, game.id)
    await call.message.answer(
        **renderer.render('on_success_enter_player', game=game, planet=planet),
        reply_markup=kb.ingame_keyboard(False),
    )
    if game.status == GameStatus.WAITING:
        await notify_lobby_on_join_leave(
            call.bot, game, planet,
            game_client, session,
            partial(renderer.render, key='player_enter_notification')
        )
    elif game.status == GameStatus.ROUND:
        all_planets_and_cities = await game_client.get_all_planets_and_cities(session, game.id)
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

