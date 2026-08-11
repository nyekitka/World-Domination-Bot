from collections.abc import Awaitable, Callable
from typing import ParamSpec

from aiogram import Bot, types

from database.schemas import CityDto, GameDto, PlanetDto
from game.schemas import FAILURE_INTERPRETATIONS, FailureReason, OrderInfo, OrderType
from keyboards import keyboards as kb
from messages.renderer import MessageRenderer
from storage.clients.messages import MessagesClient
from storage.schemas import MessageType

Markup = (
    types.InlineKeyboardMarkup
    | types.ReplyKeyboardMarkup
    | types.ReplyKeyboardRemove
    | types.ForceReply
    | None
)

P = ParamSpec('P')


async def method_executor_call[**P](
    method: Callable[P, Awaitable[FailureReason]],
    call: types.CallbackQuery,
    renderer: MessageRenderer,
    *args: P.args,
) -> bool:
    result = await method(*args)
    if result != FailureReason.SUCCESS:
        await call.answer(
            renderer.render(FAILURE_INTERPRETATIONS[result])['text'], True
        )
        return False
    await call.answer()
    return True


async def sync_method_executor_call[**P](
    method: Callable[P, FailureReason],
    call: types.CallbackQuery,
    renderer: MessageRenderer,
    *args: P.args,
) -> bool:
    result = method(*args)
    if result != FailureReason.SUCCESS:
        await call.answer(
            renderer.render(FAILURE_INTERPRETATIONS[result])['text'], True
        )
        return False
    await call.answer()
    return True


async def method_executor_msg[**P](
    bot: Bot,
    method: Callable[P, Awaitable[FailureReason]],
    userid: int,
    renderer: MessageRenderer,
    *args: P.args,
    reply_markup: Markup = None,
) -> bool:
    result = await method(*args)
    if result != FailureReason.SUCCESS:
        await bot.send_message(
            userid,
            **renderer.render(FAILURE_INTERPRETATIONS[result]),
            reply_markup=reply_markup,
        )
        return False
    return True


async def send_all_info(
    bot: Bot,
    game: GameDto,
    planets_and_cities: dict[int, tuple[PlanetDto, list[CityDto]]],
    planet_id: int,
    order_info: OrderInfo,
    user_id: int,
    messages_client: MessagesClient,
    sanctioned_planets: list[PlanetDto],
    renderer: MessageRenderer,
):
    planet, planet_cities = planets_and_cities.pop(planet_id)
    planet_cities.sort(key=lambda city: city.name)
    other_planets = [val[0] for val in planets_and_cities.values()]
    await bot.send_message(
        user_id,
        **renderer.render(
            'start_round_for_players',
            game=game,
        ),
    )
    city_msg = await bot.send_message(
        user_id,
        **renderer.render(
            'common_planet_info',
            planet=planet,
            cities=planet_cities,
        ),
        reply_markup=kb.city_keyboard(
            game.round,
            planet,
            planet_cities,
            order_info.get(OrderType.SHIELD, []),
            order_info.get(OrderType.DEVELOP, []),
        ),
    )
    messages_client.set_info_message_id(user_id, MessageType.CITY, city_msg.message_id)

    ikm = (
        kb.invent_meteorites_keyboard(planet, order_info.get(OrderType.INVENT, False))
        if not planet.is_invented
        else kb.meteorites_keyboard(planet, order_info.get(OrderType.CREATE, 0))
    )
    meteorites_msg = await bot.send_message(
        user_id,
        **renderer.render(
            'meteorites_info',
            planet=planet,
        ),
        reply_markup=ikm,
    )
    messages_client.set_info_message_id(
        user_id, MessageType.METEORITES, meteorites_msg.message_id
    )

    sanctioned_planets_names = [planet.name for planet in sanctioned_planets]
    sanctions_msg = await bot.send_message(
        user_id,
        **renderer.render(
            'sanctions_info',
            sanctioned_planets=sanctioned_planets_names,
        ),
        reply_markup=kb.sanctions_keyboard(
            planet, other_planets, order_info.get(OrderType.SANCTIONS, [])
        ),
    )
    messages_client.set_info_message_id(
        user_id, MessageType.SANCTIONS, sanctions_msg.message_id
    )

    eco_msg = await bot.send_message(
        user_id,
        **renderer.render(
            'eco_info',
            game=game,
        ),
        reply_markup=kb.eco_keyboard(planet, order_info.get(OrderType.ECO, False)),
    )
    messages_client.set_info_message_id(user_id, MessageType.ECO, eco_msg.message_id)

    first_planet_id = min(planets_and_cities.keys())
    first_planet, first_planet_cities = planets_and_cities[first_planet_id]

    msg = await bot.send_message(
        user_id,
        **renderer.render(
            'other_planet_info',
            planet=first_planet,
            cities=first_planet_cities,
        ),
        reply_markup=kb.other_planets_keyboard(
            game.round,
            planet,
            first_planet,
            first_planet_cities,
            order_info.get(OrderType.ATTACK, []),
            list(planets_and_cities.keys()),
        ),
    )
    messages_client.set_info_message_id(
        user_id,
        MessageType.ATTACK,
        msg.message_id,
    )
