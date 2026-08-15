import asyncio
import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.admin import AdminFilter
from app.filters.buttons import InlineButtonFilter, ReplyButtonFilter
from app.filters.state import BotStates
from app.handlers.round_loop import get_round_notifier
from app.utils import method_executor_msg, send_all_info, sync_method_executor_call
from database.clients.game import GameClient
from database.clients.info import InfoClient
from database.clients.user import UserClient
from database.schemas import GameDto, GameStatus, PlanetDto, UserDto
from game.config import game_config
from keyboards import keyboards as kb
from keyboards.schemas import Action, ActionType, get_action_from_data, validate_action
from messages.renderer import MessageRenderer
from storage.clients.actions import ActionsClient
from storage.clients.messages import MessagesClient
from storage.schemas import MessageType

ingame_router = Router()
logger = logging.getLogger(__name__)


async def start_round(
    message: types.Message,
    user_client: UserClient,
    messages_client: MessagesClient,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'ingame_router.start_round: Admin id=%s is starting a new round',
        message.from_user.id,
    )
    res = await method_executor_msg(
        message.bot,
        game_client.start_new_round,
        message.from_user.id,
        renderer,
        session,
        message.from_user.id,
    )
    if not res:
        return

    user = await user_client.get_user(session, message.from_user.id)
    active_admins = await game_client.get_all_active_admins(session, user.game_id)
    active_players = await game_client.get_all_active_players(session, user.game_id)
    acitve_players_ids = [
        player.tg_id
        for player in active_players
    ]
    game: GameDto = await game_client.get_game(session, user.game_id)

    for admin in active_admins:
        await message.bot.send_message(
            admin.tg_id,
            **renderer.render('start_round_for_admins', game=game),
            reply_markup=types.ReplyKeyboardRemove(),
        )

    all_planets_and_cities = await game_client.get_all_planets_and_cities(
        session, game.id
    )
    for pl_id in all_planets_and_cities:
        planet, _ = all_planets_and_cities[pl_id]
        actions_client.set_balance(planet.id, planet.balance, actions_client.MONEY_KEY)
        actions_client.set_balance(
            planet.id, planet.meteorites, actions_client.METEORITES_KEY
        )
        if planet.owner_id in acitve_players_ids:
            sanctioned_planets = await game_client.get_sanctioned_planets(session, pl_id)
            await send_all_info(
                bot=message.bot,
                game=game,
                planets_and_cities=all_planets_and_cities.copy(),
                planet_id=pl_id,
                order_info={},
                user_id=planet.owner_id,
                messages_client=messages_client,
                sanctioned_planets=sanctioned_planets,
                renderer=renderer,
            )
    round_notifier = get_round_notifier(
        bot=message.bot,
        game=game,
        game_client=game_client,
        actions_client=actions_client,
        info_client=info_client,
        messages_client=messages_client,
        session=session,
        renderer=renderer,
    )
    await session.commit()
    await round_notifier.run_loop()


@ingame_router.message(ReplyButtonFilter('Начать игру'), AdminFilter())
async def start_game(
    message: types.Message,
    user_client: UserClient,
    messages_client: MessagesClient,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    await start_round(
        message,
        user_client,
        messages_client,
        game_client,
        actions_client,
        info_client,
        session,
        renderer,
    )


@ingame_router.message(Command('snround'), AdminFilter())
async def start_new_round(
    message: types.Message,
    user_client: UserClient,
    messages_client: MessagesClient,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    await start_round(
        message,
        user_client,
        messages_client,
        game_client,
        actions_client,
        info_client,
        session,
        renderer,
    )


@ingame_router.message(
    Command('endgame'),
    AdminFilter(),
)
async def end_the_game(
    message: types.Message,
    user_client: UserClient,
    game_client: GameClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'ingame_router.end_the_game: Admin id=%s is ending the game',
        message.from_user.id,
    )
    user: UserDto = await user_client.get_user(session, message.from_user.id)
    if user.game_id is None:
        message.answer(**renderer.render('ending_outside'))
        return
    game: GameDto = await user_client.get_game(session, user.game_id)

    admins_list = await game_client.get_all_active_admins(session, game.id)
    players_list = await game_client.get_all_active_players(session, game.id)

    for admin in admins_list:
        await message.bot.send_message(
            admin.tg_id, **renderer.render('game_interrupted_report'),
            reply_markup=kb.start_keyboard(True)
        )
    for player in players_list:
        await message.bot.send_message(
            player.tg_id, **renderer.render('game_interrupted_message'),
            reply_markup=kb.start_keyboard(False)
        )
    await game_client.end_game(session, game.id)


@ingame_router.callback_query(lambda call: validate_action(call.data))
async def handle_action(
    call: types.CallbackQuery,
    state: FSMContext,
    user_client: UserClient,
    game_client: GameClient,
    messages_client: MessagesClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    action = get_action_from_data(call.data)
    logger.info(
        'ingame_router.handle_action: User id=%s is performing action %s',
        call.from_user.id,
        action.action_type,
    )
    user = await user_client.get_user(session, call.from_user.id)
    if user.game_id is None:
        call.answer(**renderer.render('action_out_of_game'))
        await call.bot.delete_message(call.from_user.id, call.message.message_id)
        return
    game: GameDto = await game_client.get_game(session, user.game_id)
    planet = await game_client.get_player_planet(
        session, call.from_user.id, user.game_id
    )
    if planet is None:
        call.answer(**renderer.render('unexpected_error'))
        await call.bot.delete_message(call.from_user.id, call.message.message_id)
        return

    old_balance = actions_client.get_balance(planet.id, actions_client.MONEY_KEY)
    old_meteorites = actions_client.get_balance(
        planet.id, actions_client.METEORITES_KEY
    )

    data = {
        'call': call,
        'action': action,
        'planet': planet,
        'state': state,
        'game': game,
        'user_client': user_client,
        'game_client': game_client,
        'actions_client': actions_client,
        'messages_client': messages_client,
        'session': session,
        'renderer': renderer,
    }
    match action.action_type:
        case ActionType.ATTACK:
            await handle_attack_action(**data)
        case ActionType.DEVELOP | ActionType.SHIELD:
            await handle_city_action(**data)
        case ActionType.CREATE:
            await handle_create_action(**data)
        case ActionType.ECO:
            await handle_eco_action(**data)
        case ActionType.SANCTIONS:
            await handle_sanctions_action(**data)
        case ActionType.INVENT:
            await handle_invent_action(**data)
        case ActionType.NEGOTIATE:
            await handle_negotiate_action(**data)
        case ActionType.TRANSACTION:
            await handle_transaction_action(**data)
            return
        case ActionType.ACCEPT_NEGOTIATIONS:
            await handle_accept_negotiations_action(**data)
        case ActionType.REFUSE_NEGOTIATIONS:
            await handle_refuse_negotiations_action(**data)
        case ActionType.END_NEGOTIATIONS:
            await handle_end_negotiations_action(**data)

    new_balance = actions_client.get_balance(planet.id, actions_client.MONEY_KEY)
    meteorites = actions_client.get_balance(planet.id, actions_client.METEORITES_KEY)

    if old_balance != new_balance:
        info_message_id = messages_client.get_info_message_id(
            planet.owner_id,
            MessageType.CITY,
        )
        planet.balance = new_balance
        cities = await game_client.get_cities_of_planet(session, planet.id, False)
        cities.sort(key=lambda city: city.name)
        await call.bot.edit_message_text(
            **renderer.render(
                'common_planet_info',
                planet=planet,
                cities=cities,
            ),
            chat_id=planet.owner_id,
            message_id=info_message_id,
            reply_markup=kb.city_keyboard(
                game.round,
                planet,
                cities,
                actions_client.get_shielded_cities(planet.id),
                actions_client.get_developed_cities(planet.id),
            ),
        )
    if old_meteorites != meteorites:
        planet.meteorites = meteorites
        info_message_id = messages_client.get_info_message_id(
            planet.owner_id,
            MessageType.METEORITES,
        )
        chosen_meteorites = actions_client.get_created_meteorites(planet.id)
        await call.bot.edit_message_text(
            **renderer.render('meteorites_info', planet=planet),
            chat_id=planet.owner_id,
            message_id=info_message_id,
            reply_markup=kb.meteorites_keyboard(planet, chosen_meteorites),
        )


async def handle_attack_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    result = await sync_method_executor_call(
        actions_client.attack_city, call, renderer, planet.id, action.argument
    )
    if not result:
        return

    attacked_cities = actions_client.get_attacked_cities(planet.id)
    other_planet = await game_client.get_planet_by_city_id(session, action.argument)
    all_cities = await game_client.get_cities_of_planet(
        session, other_planet.id, with_rates=False
    )
    all_planets_in_game = await game_client.get_planets_of_game(session, planet.game_id, False)
    other_planet_ids = [
        planet_in_game.id
        for planet_in_game in all_planets_in_game
        if planet_in_game.id != planet.id
    ]

    await call.message.edit_reply_markup(
        reply_markup=kb.other_planets_keyboard(
            game.round, planet, other_planet, all_cities, attacked_cities, other_planet_ids
        )
    )


async def handle_city_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    if action.action_type == ActionType.DEVELOP:
        result = await sync_method_executor_call(
            actions_client.develop_city, call, renderer, planet.id, action.argument
        )
    else:
        result = await sync_method_executor_call(
            actions_client.shield_city, call, renderer, planet.id, action.argument
        )

    if not result:
        return

    shielded_cities = actions_client.get_shielded_cities(planet.id)
    developed_cities = actions_client.get_developed_cities(planet.id)

    all_cities = await game_client.get_cities_of_planet(
        session, planet.id, with_rates=False
    )

    await call.message.edit_reply_markup(
        reply_markup=kb.city_keyboard(
            game.round, planet, all_cities, shielded_cities, developed_cities
        )
    )


async def handle_create_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    actions_client: ActionsClient,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    result = await sync_method_executor_call(
        actions_client.create_meteorites, call, renderer, planet.id, action.argument
    )
    if not result:
        return

    chosen = actions_client.get_created_meteorites(planet.id)

    await call.message.edit_reply_markup(
        reply_markup=kb.meteorites_keyboard(planet, chosen)
    )


async def handle_eco_action(
    call: types.CallbackQuery,
    planet: PlanetDto,
    actions_client: ActionsClient,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    result = await sync_method_executor_call(
        actions_client.eco_boost, call, renderer, planet.id
    )
    if not result:
        return

    is_eco_boosted = actions_client.get_eco_boost(planet.id)

    await call.message.edit_reply_markup(
        reply_markup=kb.eco_keyboard(planet, is_eco_boosted)
    )


async def handle_sanctions_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    result = await sync_method_executor_call(
        actions_client.sanction_planet, call, renderer, planet.id, action.argument
    )
    if not result:
        return

    sanctioned_planets = actions_client.get_sanctioned_planets(planet.id)
    other_planets = await game_client.get_planets_of_game(session, game.id, False)

    await call.message.edit_reply_markup(
        reply_markup=kb.sanctions_keyboard(planet, other_planets, sanctioned_planets)
    )


async def handle_invent_action(
    call: types.CallbackQuery,
    planet: PlanetDto,
    actions_client: ActionsClient,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    result = await sync_method_executor_call(
        actions_client.invent, call, renderer, planet.id
    )
    if not result:
        return

    is_invented = actions_client.get_invented(planet.id)

    await call.message.edit_reply_markup(
        reply_markup=kb.invent_meteorites_keyboard(planet, is_invented)
    )


async def handle_negotiate_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    user_client: UserClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    await call.answer()
    to_planet = await user_client.get_planet(session, action.argument, False)
    user = await user_client.get_user(session, to_planet.owner_id)
    if user is None or user.game_id is None:
        await call.message.answer(
            **renderer.render(
                'negotiator_offline',
                to_planet=to_planet,
            )
        )
        return
    await call.message.answer(
        **renderer.render(
            'wait_for_acception',
            to_planet=to_planet,
        )
    )
    message = await call.bot.send_message(
        to_planet.owner_id,
        **renderer.render(
            'negotiations_offer',
            from_planet=planet,
        ),
        reply_markup=kb.negotiations_offer_keyboard(to_planet, planet),
    )
    messages_client.set_planet_message_id(
        to_planet.owner_id,
        planet.id,
        MessageType.NEGOTIATIONS_NOTIFICATION,
        message.message_id,
    )


async def handle_accept_negotiations_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    from_planet = await game_client.get_planet(session, action.argument, False)
    result = await sync_method_executor_call(
        actions_client.make_negotiations, call, renderer, planet.id, from_planet.id,
    )
    if not result:
        return

    message = await call.message.answer(
        **renderer.render(
            'waiting_for_diplomatist',
            from_planet=from_planet,
        ),
        reply_markup=kb.end_negotiations_keyboard(planet, from_planet),
    )
    messages_client.set_planet_message_id(
        planet.owner_id,
        from_planet.id,
        MessageType.NEGOTIATIONS_END,
        message.message_id,
    )
    await call.message.delete()
    messages_client.delete_planet_message_ids(
        planet.owner_id, MessageType.NEGOTIATIONS_NOTIFICATION, from_planet.id
    )

    active_admins = await game_client.get_all_active_admins(session, game.id)
    for admin in active_admins:
        await call.bot.send_message(
            admin.tg_id,
            **renderer.render(
                'negotiations_for_admin',
                from_planet=from_planet,
                to_planet=planet,
            ),
        )

    await call.bot.send_message(
        from_planet.owner_id,
        **renderer.render(
            'negotiations_accepted',
            to_planet=planet,
        ),
    )


async def handle_refuse_negotiations_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game_client: GameClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    await call.answer()
    await call.message.delete()
    messages_client.delete_planet_message_ids(
        planet.owner_id, MessageType.NEGOTIATIONS_NOTIFICATION, action.argument
    )

    from_planet = await game_client.get_planet(session, action.argument, False)
    await call.bot.send_message(
        from_planet.owner_id,
        **renderer.render(
            'negotiations_refused',
            to_planet=planet,
        ),
    )


async def handle_end_negotiations_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    from_planet = await game_client.get_planet(session, action.argument)
    result = await sync_method_executor_call(
        actions_client.end_negotiations,
        call,
        renderer,
        planet,
    )
    if not result:
        return

    active_admins = await game_client.get_all_active_admins(session, game.id)
    for admin in active_admins:
        await call.bot.send_message(
            admin.tg_id,
            **renderer.render(
                'negotiations_ended_for_admin',
                to_planet=planet,
            ),
        )

    await call.message.answer(**renderer.render('negotiations_ended'))
    messages_client.delete_planet_message_ids(
        planet.owner_id, MessageType.NEGOTIATIONS_END, from_planet.id
    )
    await call.message.delete()


async def handle_transaction_action(
    call: types.CallbackQuery,
    action: Action,
    state: FSMContext,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    session: AsyncSession,
    renderer: MessageRenderer,
    *args,
    **kwargs,
):
    await call.answer()

    to_planet = await game_client.get_planet(session, action.argument, False)

    await state.set_state(BotStates.transaction_state)
    transaction_data = {'from_planet': planet, 'to_planet': to_planet, 'game': game}
    await state.set_data(transaction_data)
    await call.message.answer(
        **renderer.render(
            'how_much_money',
            to_planet=to_planet,
        )
    )

    await asyncio.sleep(game_config.TIME_WAITING_AMOUNT_ANSWER)

    current_data = await state.get_data()
    if current_data != transaction_data:
        return

    await state.clear()
    game = await game_client.get_game(session, game.id)
    if game.status == GameStatus.ROUND:
        await call.message.answer(**renderer.render('waiting_time_expired'))


@ingame_router.message(BotStates.transaction_state)
async def set_amount_of_money(
    message: types.Message,
    state: FSMContext,
    game_client: GameClient,
    actions_client: ActionsClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'ingame_router.set_amount_of_money: User id=%s is setting amount of money for transaction',
        message.from_user.id,
    )
    amount = None
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(**renderer.render('wrong_answer'))
        return
    if amount == 0:
        await state.clear()
        return
    elif amount < 0:
        await message.answer(**renderer.render('wrong_answer'))
        return

    data = await state.get_data()
    game = data['game']
    from_planet = data['from_planet']
    to_planet = data['to_planet']

    # check current balance which is stored
    current_balance = actions_client.get_balance(from_planet.id, actions_client.MONEY_KEY)
    if amount > current_balance:
        await message.answer(**renderer.render('not_enough_money_for_transaction'))
        return

    from_planet_cities = await game_client.get_cities_of_planet(
        session, from_planet.id, False,
    )
    to_planet_cities = await game_client.get_cities_of_planet(
        session, to_planet.id, False,
    )
    res = await method_executor_msg(
        message.bot,
        game_client.transfer,
        message.from_user.id,
        renderer,
        session,
        from_planet.id,
        to_planet.id,
        amount,
    )
    if not res:
        return

    actions_client.set_balance(
        from_planet.id, current_balance - amount, actions_client.MONEY_KEY,
    )
    to_planet_balance = actions_client.get_balance(to_planet.id, actions_client.MONEY_KEY)
    actions_client.set_balance(
        to_planet.id, to_planet_balance + amount, actions_client.MONEY_KEY,
    )
    from_planet.balance = current_balance - amount
    to_planet.balance = to_planet_balance + amount

    from_city_id = messages_client.get_info_message_id(
        from_planet.owner_id, MessageType.CITY
    )
    to_city_id = messages_client.get_info_message_id(
        to_planet.owner_id, MessageType.CITY
    )
    await message.bot.edit_message_text(
        **renderer.render(
            'common_planet_info',
            planet=from_planet,
            cities=from_planet_cities,
        ),
        chat_id=from_planet.owner_id,
        message_id=from_city_id,
        reply_markup=kb.city_keyboard(
            game.round,
            from_planet,
            from_planet_cities,
            actions_client.get_shielded_cities(from_planet.id),
            actions_client.get_developed_cities(from_planet.id),
        ),
    )
    await message.bot.edit_message_text(
        **renderer.render(
            'common_planet_info',
            planet=to_planet,
            cities=to_planet_cities,
        ),
        chat_id=to_planet.owner_id,
        message_id=to_city_id,
        reply_markup=kb.city_keyboard(
            game.round,
            to_planet,
            to_planet_cities,
            actions_client.get_shielded_cities(to_planet.id),
            actions_client.get_developed_cities(to_planet.id),
        ),
    )
    await message.answer(
        **renderer.render('successful_transaction', to_planet=to_planet)
    )
    await message.bot.send_message(
        to_planet.owner_id,
        **renderer.render(
            'transaction_notification',
            from_planet=from_planet,
            amount=amount,
        ),
    )
    await state.clear()


@ingame_router.callback_query(InlineButtonFilter('other_planet_info'))
async def switch_other_planet(
    call: types.CallbackQuery,
    game_client: GameClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    _, planet_id, other_planet_id = call.data.split()

    planet = await game_client.get_planet(session, int(planet_id), False)
    game = await game_client.get_game(session, planet.game_id)
    other_planet = await game_client.get_planet(session, int(other_planet_id), False)
    other_planet_cities = await game_client.get_cities_of_planet(session, int(other_planet_id), False)
    planets_in_game = await game_client.get_planets_of_game(session, planet.game_id, False)

    other_planet_ids = [
        planet_in_game.id
        for planet_in_game in planets_in_game
        if planet_in_game.id != planet.id
    ]
    attacked_cities_ids = actions_client.get_attacked_cities(planet.id)

    await call.answer()
    await call.message.edit_text(
        **renderer.render(
            'other_planet_info',
            planet=other_planet,
            cities=other_planet_cities,
        ),
        reply_markup=kb.other_planets_keyboard(
            game.round,
            planet,
            other_planet,
            other_planet_cities,
            attacked_cities_ids,
            other_planet_ids,
        )
    )
