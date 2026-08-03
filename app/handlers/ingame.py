import asyncio
import logging

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.admin import AdminFilter
from app.filters.buttons import ReplyButtonFilter
from app.filters.state import BotStates
from app.handlers.round_loop import get_round_notifier
from app.utils import method_executor_msg, send_all_info, sync_method_executor_call
from database.clients.game import GameClient
from database.clients.info import InfoClient
from database.clients.user import UserClient
from database.schemas import GameDto, GameStatus, PlanetDto, UserDto
from game.config import game_config
from keyboards import keyboards as kb
from keyboards.schemas import Action, ActionType, validate_action_json
from messager import messager
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
):
    logger.info(
        'ingame_router.start_round: Admin id=%s is starting a new round',
        message.from_user.id
    )
    res = await method_executor_msg(
        message.bot,
        game_client.start_new_round,
        message.from_user.id,
        session, message.from_user.id
    )
    if not res:
        return

    await session.commit()
    
    user = await user_client.get_user(session, message.from_user.id)
    active_admins = await game_client.get_all_active_admins(session, user.game_id)
    game: GameDto = await game_client.get_game(session, user.game_id)

    for admin in active_admins:
        await message.bot.send_message(
            admin.tg_id,
            messager.round_admins(game.round),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=types.ReplyKeyboardRemove(),
        )
    
    all_planets_and_cities = await game_client.get_all_planets_and_cities(session, game.id)
    for pl_id in all_planets_and_cities:
        planet, _ = all_planets_and_cities[pl_id]
        await send_all_info(
            bot=message.bot,
            game=game,
            planets_and_cities=all_planets_and_cities,
            planet_id=pl_id,
            order_info=dict(),
            user_id=planet.owner_id,
            messages_client=messages_client,
        )
    round_notifier = get_round_notifier(
        bot=message.bot,
        game=game,
        game_client=game_client,
        actions_client=actions_client,
        info_client=info_client,
        messages_client=messages_client,
        session=session,
    )
    await session.commit()
    await round_notifier.run_loop()


@ingame_router.message(
    ReplyButtonFilter('Начать игру'),
    AdminFilter()
)
async def start_game(
    message: types.Message,
    user_client: UserClient,
    messages_client: MessagesClient,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    session: AsyncSession
):
    await start_round(
        message,
        user_client,
        messages_client,
        game_client,
        actions_client,
        info_client,
        session,
    )


@ingame_router.message(
    Command('snround'),
    AdminFilter()
)
async def start_new_round(
    message: types.Message,
    user_client: UserClient,
    messages_client: MessagesClient,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    session: AsyncSession,
):
    await start_round(
        message,
        user_client,
        messages_client,
        game_client,
        actions_client,
        info_client,
        session,
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
):
    logger.info(
        'ingame_router.end_the_game: Admin id=%s is ending the game',
        message.from_user.id
    )
    user: UserDto = await user_client.get_user(session, message.from_user.id)
    if user.game_id is None:
        message.answer(messager.ending_outside())
        return
    game: GameDto = await user_client.get_game(session, user.game_id)

    admins_list = await game_client.get_all_active_admins(session, game.id)
    players_list = await game_client.get_all_active_players(session, game.id)

    for admin in admins_list:
        await message.bot.send_message(
            admin.tg_id,
            messager.game_interrupted_report()
        )
    for player in players_list:
        await message.bot.send_message(
            player.tg_id,
            messager.game_interrupted_message()
        )
    await game_client.end_game(session, game.id)


@ingame_router.callback_query(lambda call: validate_action_json(call.data))
async def handle_action(
    call: types.CallbackQuery,
    state: FSMContext,
    user_client: UserClient,
    game_client: GameClient,
    messages_client: MessagesClient,
    actions_client: ActionsClient,
    session: AsyncSession,
):
    action = Action.model_validate_json(call.data)
    logger.info(
        'ingame_router.handle_action: User id=%s is performing action %s',
        call.from_user.id, action.action_type
    )
    user = await user_client.get_user(session, call.from_user.id)
    if user.game_id is None:
        call.answer(messager.action_out_of_game())
        await call.bot.delete_message(call.from_user.id, call.message.message_id)
        return
    game: GameDto = await game_client.get_game(session, user.game_id)
    planet = await game_client.get_player_planet(session, call.from_user.id, user.game_id, False)
    if planet is None:
        call.answer(messager.unexpected_error())
        await call.bot.delete_message(call.from_user.id, call.message.message_id)
        return
    
    old_balance = actions_client.get_balance(planet.id, actions_client.MONEY_KEY)
    old_meteorites = actions_client.get_balance(planet.id, actions_client.METEORITES_KEY)

    data = {
        'call': call,
        'action': action,
        'planet': planet,
        'state': state,
        'game': game,
        'game_client': game_client,
        'actions_client': actions_client,
        'messages_client': messages_client,
        'session': session,
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
        cities = await game_client.get_cities_of_planet(session, planet.id, False, False)
        await call.bot.edit_message_text(
            messager.city_stats_message(
                planet, cities
            ),
            chat_id=planet.owner_id,
            message_id=info_message_id,
            reply_markup=kb.city_keyboard(
                game.round,
                planet, cities,
                actions_client.get_shielded_cities(planet.id),
                actions_client.get_developed_cities(planet.id),
            ),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    if old_meteorites != meteorites:
        planet.meteorites = meteorites
        info_message_id = messages_client.get_info_message_id(
            planet.owner_id,
            MessageType.METEORITES,
        )
        chosen_meteorites = actions_client.get_created_meteorites(planet.id)
        await call.bot.edit_message_text(
            messager.meteorites_message(planet),
            chat_id=planet.owner_id,
            message_id=info_message_id,
            reply_markup=kb.meteorites_keyboard(planet, chosen_meteorites),
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    await game_client.spend(session, planet.id, old_balance - new_balance, old_meteorites - meteorites)

async def handle_attack_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    *args, **kwargs,
):
    result = await sync_method_executor_call(actions_client.attack_city, call, planet.id, action.argument)
    if not result:
        return

    attacked_cities = actions_client.get_attacked_cities(planet.id)
    other_planet = await game_client.get_planet_by_city_id(session, action.argument)
    all_cities = await game_client.get_cities_of_planet(session, other_planet.id, with_rates=False)

    await call.message.edit_reply_markup(
        reply_markup=kb.other_planets_keyboard(
            game.round, planet, other_planet,
            all_cities, attacked_cities
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
    *args, **kwargs,
):
    if action.action_type == ActionType.DEVELOP:
        result = await sync_method_executor_call(actions_client.develop_city, call, planet.id, action.argument)
    else:
        result = await sync_method_executor_call(actions_client.shield_city, call, planet.id, action.argument)
    
    if not result:
        return None
    
    shielded_cities = actions_client.get_shielded_cities(planet.id)
    developed_cities = actions_client.get_developed_cities(planet.id)

    all_cities = await game_client.get_cities_of_planet(session, planet.id, with_rates=False)

    await call.message.edit_reply_markup(
        reply_markup=kb.city_keyboard(
            game.round, planet, all_cities,
            shielded_cities, developed_cities
        )
    )


async def handle_create_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    actions_client: ActionsClient,
    *args, **kwargs,    
):
    result = await sync_method_executor_call(
        actions_client.create_meteorites,
        call,
        planet.id, action.argument
    )
    if not result:
        return None

    chosen = actions_client.get_created_meteorites(planet.id)

    await call.message.edit_reply_markup(
        reply_markup=kb.meteorites_keyboard(
            planet, chosen
        )
    )


async def handle_eco_action(
    call: types.CallbackQuery,
    planet: PlanetDto,
    actions_client: ActionsClient,
    *args, **kwargs,    
):
    result = await sync_method_executor_call(
        actions_client.eco_boost,
        call, planet.id
    )
    if not result:
        return None

    is_eco_boosted = actions_client.get_eco_boost(planet.id)

    await call.message.edit_reply_markup(
        reply_markup=kb.eco_keyboard(
            planet, is_eco_boosted
        )
    )


async def handle_sanctions_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    session: AsyncSession,
    *args, **kwargs,
):
    result = await sync_method_executor_call(
        actions_client.sanction_planet,
        call, planet.id,
        action.argument
    )
    if not result:
        return None

    sanctioned_planets = actions_client.get_sanctioned_planets(planet.id)
    other_planets = await game_client.get_planets_of_game(session, game.id, False)

    await call.message.edit_reply_markup(
        reply_markup=kb.sanctions_keyboard(
            planet, other_planets, sanctioned_planets
        )
    )


async def handle_invent_action(
    call: types.CallbackQuery,
    planet: PlanetDto,
    actions_client: ActionsClient,
    *args, **kwargs,    
):
    result = await sync_method_executor_call(
        actions_client.invent,
        call, planet.id
    )
    if not result:
        return None

    is_invented = actions_client.get_invented(planet.id)

    await call.message.edit_reply_markup(
        reply_markup=kb.invent_meteorites_keyboard(
            planet, is_invented
        )
    )


async def handle_negotiate_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game_client: GameClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    *args, **kwargs,
):
    await call.answer()
    planet_to = await game_client.get_planet(session, action.argument, False)
    if planet_to.owner_id is None:
        await call.message.answer(
            messager.nobody_online(planet_to.name)
        )
        return
    await call.message.answer(messager.wait_for_acception(planet_to.name))
    message = await call.bot.send_message(
        planet_to.owner_id,
        messager.negotiations_offer(planet.name),
        reply_markup=kb.negotiations_offer_keyboard(planet_to, planet)
    )
    messages_client.set_planet_message_id(
        planet_to.owner_id, planet_to.id,
        MessageType.NEGOTIATIONS, message.message_id
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
    *args, **kwargs,    
):
    from_planet = await game_client.get_planet(session, action.argument, False)
    result = await sync_method_executor_call(
        actions_client.make_negotiations,
        call,
        from_planet.id, planet.id
    )
    if not result:
        return
    
    message = await call.message.answer(
        messager.wait_for_diplomatist(from_planet.name),
        reply_markup=kb.end_negotiations_keyboard(planet, from_planet)
    )
    messages_client.set_planet_message_id(
        planet.owner_id, planet.id,
        MessageType.NEGOTIATIONS, message.message_id
    )
    await call.message.delete()
    
    active_admins = await game_client.get_all_active_admins(session, game.id)
    for admin in active_admins:
        await call.bot.send_message(
            admin.tg_id,
            messager.neg_accept_for_admin(
                planet.name, from_planet.name
            )
        )

    await call.bot.send_message(
        from_planet.owner_id,
        messager.negotiations_accepted(planet.name)
    )


async def handle_refuse_negotiations_action(
    call: types.CallbackQuery,
    action: Action,
    planet: PlanetDto,
    game_client: GameClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    *args, **kwargs,   
):
    await call.answer()

    from_planet = await game_client.get_planet(session, action.argument, False)
    await call.bot.send_message(
        from_planet.owner_id,
        messager.negotiations_denied(planet.name),
        messages_client.delete_planet_message_ids(
            planet.owner_id,
            MessageType.NEGOTIATIONS,
            from_planet.id
        )
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
    *args, **kwargs,  
):
    from_planet = await game_client.get_planet(session, action.argument)
    result = await sync_method_executor_call(
        actions_client.end_negotiations,
        call,
        from_planet,
    )
    if not result:
        return
    
    active_admins = await game_client.get_all_active_admins(session, game.id)
    for admin in active_admins:
        await call.bot.send_message(
            admin.tg_id,
            messager.negotiations_ended_admin(planet.name)
        )
    
    await call.message.answer(messager.negotiations_ended())
    messages_client.delete_planet_message_ids(
        planet.owner_id, MessageType.NEGOTIATIONS, from_planet.id
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
    *args, **kwargs,
):
    await call.answer()

    other_planet = await game_client.get_planet(session, action.argument, False)

    await state.set_state(BotStates.transaction_state)
    transaction_data = {
        'from_planet': planet,
        'to_planet': other_planet,
        'game': game
    }
    await state.set_data(transaction_data)
    await call.message.answer(messager.how_much_money(other_planet.name))

    await asyncio.sleep(game_config.TIME_WAITING_AMOUNT_ANSWER)

    current_data = await state.get_data()
    if current_data != transaction_data:
        return
    
    await state.clear()
    game = await game_client.get_game(session, game.id)
    if game.status == GameStatus.ROUND:
        await call.message.answer(messager.waiting_time_expired())


@ingame_router.message(BotStates.transaction_state)
async def set_amount_of_money(
    message: types.Message,
    state: FSMContext,
    game_client: GameClient,
    actions_client: ActionsClient,
    messages_client: MessagesClient,
    session: AsyncSession,
):
    logger.info(
        'ingame_router.set_amount_of_money: User id=%s is setting amount of money for transaction',
        message.from_user.id
    )
    amount = None
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(messager.wrong_answer())
        return
    if amount == 0:
        await state.clear()
        return
    elif amount < 0:
        await message.answer(messager.wrong_answer())
        return

    data = await state.get_data()
    game = data['game']
    from_planet = data['from_planet']
    to_planet = data['to_planet']

    # check current balance which is stored
    current_balance = actions_client.get_balance(game.id, actions_client.MONEY_KEY)
    if amount > current_balance:
        await message.answer(messager.not_enough_money_for_transaction())
        return
    
    from_planet_cities = await game_client.get_cities_of_planet(session, from_planet.id, False, False)
    to_planet_cities = await game_client.get_cities_of_planet(session, to_planet.id, False, False)
    res = await method_executor_msg(
        message.bot,
        game_client.transfer,
        message.from_user.id,
        session, from_planet.id, to_planet.id, amount
    )
    if not res:
        return

    actions_client.set_balance(from_planet.id, actions_client.MONEY_KEY, current_balance - amount)
    actions_client.set_balance(to_planet.id, actions_client.MONEY_KEY, current_balance + amount)
    from_planet.balance -= amount
    to_planet.balance += amount

    from_city_id = messages_client.get_info_message_id(from_planet.owner_id, MessageType.CITY)
    to_city_id = messages_client.get_info_message_id(to_planet.owner_id, MessageType.CITY)
    await message.bot.edit_message_text(
        messager.city_stats_message(from_planet, from_planet_cities),
        chat_id=from_planet.owner_id,
        message_id=from_city_id,
        reply_markup=kb.city_keyboard(
            game.round,
            from_planet,
            from_planet_cities,
            actions_client.get_shielded_cities(from_planet.id),
            actions_client.get_developed_cities(from_planet.id),
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await message.bot.edit_message_text(
        messager.city_stats_message(to_planet, to_planet_cities),
        chat_id=to_planet.owner_id,
        message_id=to_city_id,
        reply_markup=kb.city_keyboard(
            game.round,
            to_planet,
            to_planet_cities,
            actions_client.get_shielded_cities(to_planet.id),
            actions_client.get_developed_cities(to_planet.id),
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await message.answer(messager.successful_transaction(to_planet.name))
    await message.bot.send_message(
        to_planet.owner_id,
        messager.transaction_notification(from_planet.name, amount),
    )
    await state.clear()
