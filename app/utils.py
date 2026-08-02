from typing import Any, Awaitable, Callable, ParamSpec

from aiogram import Bot, types
from aiogram.enums import ParseMode

from database.schemas import CityDto, GameDto, PlanetDto
from game.schemas import FailureReason, FAILURE_INTERPRETATIONS, OrderInfo, OrderType
from keyboards import keyboards as kb
from messages import messager
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


async def method_executor_call(
    method: Callable[P, Awaitable[FailureReason]],
    call: types.CallbackQuery,
    *args: P.args,
) -> bool:
    result = await method(*args)
    if result != FailureReason.SUCCESS:
        call.answer(FAILURE_INTERPRETATIONS[result], True)
        return False
    await call.answer()
    return True

async def sync_method_executor_call(
    method: Callable[P, FailureReason],
    call: types.CallbackQuery,
    *args: P.args,
) -> bool:
    result = method(*args)
    if result != FailureReason.SUCCESS:
        call.answer(FAILURE_INTERPRETATIONS[result], True)
        return False
    await call.answer()
    return True

async def method_executor_msg(
    bot: Bot,
    method: Callable[P, Awaitable[FailureReason]],
    userid: int,
    *args: P.args,
    reply_markup: Markup = None
) -> bool:
    result = await method(*args)
    if result != FailureReason.SUCCESS:
        await bot.send_message(
            userid,
            FAILURE_INTERPRETATIONS[result],
            reply_markup=reply_markup
        )
        return False
    return True

def tag_person(name: str, id: int) -> str:
    return f'[{name}](tg://user?id={id})'


async def send_all_info(
    bot: Bot,
    game: GameDto,
    planets_and_cities: dict[int, tuple[PlanetDto, list[CityDto]]],
    planet_id: int,
    order_info: OrderInfo,
    user_id: int,
    messages_client: MessagesClient,
):
    planet, planet_cities = planets_and_cities.pop(planet_id)
    other_planets = [val[0] for val in planets_and_cities.values()]
    await bot.send_message(
        user_id,
        messager.round_message(game.round),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    city_msg = await bot.send_message(
        user_id,
        messager.city_stats_message(planet, planet_cities),
        reply_markup=kb.city_keyboard(
            game.round,
            planet,
            planet_cities,
            order_info.get(OrderType.SHIELD, []),
            order_info.get(OrderType.DEVELOP, [])
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    messages_client.set_info_message_id(user_id, MessageType.CITY, city_msg.message_id)

    ikm = (
        kb.invent_meteorites_keyboard(planet, order_info.get(OrderType.INVENT, False))
        if not planet.is_invented
        else kb.meteorites_keyboard(planet, order_info.get(OrderType.CREATE, 0))
    )
    meteorites_msg = await bot.send_message(
        user_id,
        messager.meteorites_message(planet),
        reply_markup=ikm,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    messages_client.set_info_message_id(user_id, MessageType.METEORITES, meteorites_msg.message_id)

    sanctioned_planets = [
        planet
        for planet in other_planets
        if planet.id in order_info.get(OrderType.SANCTIONS, [])
    ]
    sanctions_msg = await bot.send_message(
        user_id,
        messager.sanctions_message(sanctioned_planets),
        reply_markup=kb.sanctions_keyboard(
            planet, other_planets, order_info.get(OrderType.SANCTIONS, [])
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    messages_client.set_info_message_id(user_id, MessageType.SANCTIONS, sanctions_msg.message_id)

    eco_msg = await bot.send_message(
        user_id,
        messager.eco_message(game.ecorate),
        reply_markup=kb.eco_keyboard(planet, order_info.get(OrderType.ECO, False)),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    messages_client.set_info_message_id(user_id, MessageType.ECO, eco_msg.message_id)

    for other_planet, other_cities in planets_and_cities.values():
        msg = await bot.send_message(
            user_id,
            messager.other_planets_message(other_planet, other_cities),
            reply_markup=kb.other_planets_keyboard(
                game.round,
                planet,
                other_planet,
                other_cities,
                order_info.get(OrderType.ATTACK, []),
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        messages_client.set_planet_message_id(
            user_id,
            other_planet.id,
            MessageType.ATTACK,
            msg.message_id
        )
