from typing import Any, Callable, ParamSpec

from aiogram import Bot, types

from database.schemas import CityDto, PlanetDto
from game.schemas import FailureReason, FAILURE_INTERPRETATIONS
import keyboards as kb
from messages import messager


Markup = (
    types.InlineKeyboardMarkup
    | types.ReplyKeyboardMarkup
    | types.ReplyKeyboardRemove
    | types.ForceReply
    | None
)

P = ParamSpec('P')


async def method_executor_call(
    method: Callable[P, FailureReason],
    call: types.CallbackQuery,
    *args: P.args,
) -> bool:
    result = method(*args)
    if result != FailureReason.SUCCESS:
        await call.answer(FAILURE_INTERPRETATIONS[result], True)
        return False
    await call.answer()
    return True

async def method_executor_msg(
    bot: Bot,
    method: Callable[P, FailureReason],
    userid: int,
    *args: P.args,
    reply_markup: Markup = None
) -> bool:
    result = method(*args)
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
    nround: int,
    planet: PlanetDto,
    cities: list[CityDto],
    user_id: int
):
    await bot.send_message(
        user_id,
        messager.round_message(nround),
        parse_mode='MarkdownV2'
    )
    city_msg = await bot.send_message(
        user_id,
        messager.city_stats_message(planet, cities),
        reply_markup=kb.city_keyboard(
            nround,
            planet,
            cities,
            planet.ordered_shield_cities(),
            planet.developed_cities(),
        ),
        parse_mode="MarkdownV2",
    )
    ikm = (
        kb.invent_meteorites_keyboard(planet, planet.is_invent_in_order())
        if not planet.is_invented
        else kb.meteorites_keyboard(planet, planet.number_of_ordered_meteorites())
    )
    meteorites_msg = await bot.send_message(
        userid,
        messager.meteorites_message(planet),
        reply_markup=ikm,
        parse_mode="MarkdownV2",
    )
    sanctions_msg = await bot.send_message(
        userid,
        messager.sanctions_message(planet),
        reply_markup=kb.sanctions_keyboard(
            planet, planet.game().planets(), planet.ordered_sanctions_list()
        ),
        parse_mode="MarkdownV2",
    )
    eco_msg = await bot.send_message(
        userid,
        messager.eco_message(planet.game()),
        reply_markup=kb.eco_keyboard(planet, planet.is_planned_eco_boost()),
        parse_mode="MarkdownV2",
    )
    cursor.execute(
        """INSERT INTO InfoMessages(ID, MType, PlanetID) VALUES
                    (%s, 'City', %s),
                    (%s, 'Meteorites', %s),
                    (%s, 'Sanctions', %s),
                    (%s, 'Eco', %s)""",
        (
            city_msg.message_id,
            planet.id,
            meteorites_msg.message_id,
            planet.id,
            sanctions_msg.message_id,
            planet.id,
            eco_msg.message_id,
            planet.id,
        ),
    )
    for other_planet in planet.game().planets():
        if planet != other_planet:
            msg = await bot.send_message(
                userid,
                messager.other_planets_message(other_planet),
                reply_markup=kb.other_planets_keyboard(
                    nround,
                    planet,
                    other_planet,
                    planet.ordered_attack_cities(other_planet),
                ),
                parse_mode="MarkdownV2",
            )
            cursor.execute(
                "INSERT INTO PlanetMessages(OwnerID, PlanetID, MessageID, MType) VALUES (%s, %s, %s, 'Attack')",
                (planet.id, other_planet.id, msg.message_id),
            )
    db_connection.commit()