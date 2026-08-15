import os

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.schemas import AdminDto, CityDto, GameDto, GameStatus, PlanetDto
from game.config import game_config
from keyboards.schemas import Action, ActionType, get_action_data
from packs.pack import packs
from web_app.stats.middlewares.verifier import sign_user_id

WEB_APP_URL = os.getenv('WEB_APP_URL')


def start_keyboard(isadmin: bool):
    if isadmin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Создать лобби')],
                [KeyboardButton(text='Войти в лобби')],
            ]
        )
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Войти в лобби')]])


def choose_lobby_keyboard(games: list[GameDto]):
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.add(InlineKeyboardButton(text=str(game.id), callback_data=str(game.id)))
    return builder.adjust(4).as_markup()


# Клавиатура городов


def city_keyboard(
    nround: int,
    planet: PlanetDto,
    cities: list[CityDto],
    under_shield_ids: list[int],
    developed_ids: list[int],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    cities.sort(key=lambda x: x.name)
    for city in cities:
        if city.development == 0:
            continue
        str1, str2 = '', ''
        if city.id in developed_ids:
            str1 = '✅'
        if city.id in under_shield_ids:
            str2 = '✅'
        develop_action = Action(
            action_type=ActionType.DEVELOP,
            planet_id=planet.id,
            argument=city.id,
        )
        shield_action = Action(
            action_type=ActionType.SHIELD,
            planet_id=planet.id,
            argument=city.id,
        )
        builder.add(
            InlineKeyboardButton(
                text=f'{str1}📈 {city.name} ({game_config.DEVELOPMENT_COST} 💵)',
                callback_data=get_action_data(develop_action),
            ),
        )
        if nround > 1:
            builder.add(
                InlineKeyboardButton(
                    text=f'{str2}🛡️ {city.name} ({game_config.SHIELD_COST} 💵)',
                    callback_data=get_action_data(shield_action),
                ),
            )
    return builder.adjust(2).as_markup()


def sanctions_keyboard(
    planet: PlanetDto, other_planets: list[PlanetDto], under_sanctions_ids: list[int]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    other_planets.sort(key=lambda x: x.name)
    for other_planet in other_planets:
        if planet.id == other_planet.id:
            continue
        addition = '✅ ' if other_planet.id in under_sanctions_ids else ''
        sanctions_action = Action(
            action_type=ActionType.SANCTIONS,
            planet_id=planet.id,
            argument=other_planet.id,
        )
        builder.add(
            InlineKeyboardButton(
                text=f'{addition}{other_planet.name}',
                callback_data=get_action_data(sanctions_action),
            )
        )
    return builder.adjust(2).as_markup()


def invent_meteorites_keyboard(planet: PlanetDto, chosen: bool) -> InlineKeyboardMarkup:
    invent_action = Action(
        action_type=ActionType.INVENT,
        planet_id=planet.id,
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=('✅ ' if chosen else '')
                    + f'Разработать ({game_config.INVENTION_COST} 💵)',
                    callback_data=get_action_data(invent_action),
                )
            ]
        ]
    )


def meteorites_keyboard(planet: PlanetDto, chosen: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, game_config.MAX_METEORITES_TO_BUY + 1):
        action = Action(
            action_type=ActionType.CREATE,
            planet_id=planet.id,
            argument=i,
        )
        if chosen == i:
            builder.add(
                InlineKeyboardButton(
                    text=f'✅ {i} ({game_config.CREATE_COST * i} 💵)',
                    callback_data=get_action_data(action),
                )
            )
        else:
            builder.add(
                InlineKeyboardButton(
                    text=f'{i} ({game_config.CREATE_COST * i} 💵)',
                    callback_data=get_action_data(action),
                )
            )
    return builder.adjust(3).as_markup()


def eco_keyboard(planet: PlanetDto, chosen: bool) -> InlineKeyboardMarkup:
    action = Action(action_type=ActionType.ECO, planet_id=planet.id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✅ Отправить метеорит в аномалию'
                    if chosen
                    else 'Отправить метеорит в аномалию',
                    callback_data=get_action_data(action),
                )
            ]
        ]
    )


def other_planets_keyboard(
    nround: int,
    planet: PlanetDto,
    other_planet: PlanetDto,
    other_cities: list[CityDto],
    attacked_cities_ids: list[int],
    other_planet_ids: list[int],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    other_cities.sort(key=lambda x: x.name)
    other_planet_ids.sort()

    if nround > 1:
        for city in other_cities:
            if city.development == 0:
                continue
            add = '✅ ' if city.id in attacked_cities_ids else ''
            attack_action = Action(
                action_type=ActionType.ATTACK,
                planet_id=planet.id,
                argument=city.id,
            )
            builder.add(
                InlineKeyboardButton(
                    text=f'{add}🗡 {city.name}',
                    callback_data=get_action_data(attack_action),
                )
            )
    negotiate_action = Action(
        action_type=ActionType.NEGOTIATE,
        planet_id=planet.id,
        argument=other_planet.id,
    )
    transaction_action = Action(
        action_type=ActionType.TRANSACTION,
        planet_id=planet.id,
        argument=other_planet.id,
    )
    builder.add(
        InlineKeyboardButton(
            text='Переговоры 📞',
            callback_data=get_action_data(negotiate_action),
        ),
        InlineKeyboardButton(
            text='Перевод 💸',
            callback_data=get_action_data(transaction_action),
        ),
    )
    builder.adjust(2)
    planet_index = other_planet_ids.index(other_planet.id)

    if len(other_planet_ids) > 1:
        paginator = [
            InlineKeyboardButton(
                text='⬅️',
                callback_data=(
                    'other_planet_info '
                    f'{planet.id} '
                    f'{other_planet_ids[planet_index - 1]}'
                )
            ),
            InlineKeyboardButton(
                text='➡️',
                callback_data=(
                    'other_planet_info '
                    f'{planet.id} '
                    f'{other_planet_ids[(planet_index + 1) % len(other_planet_ids)]}'
                ),
            ),
        ]
        builder.row(*paginator)
    return builder.as_markup()



def negotiations_offer_keyboard(planet: PlanetDto, from_planet: PlanetDto):
    accept_neg = Action(
        action_type=ActionType.ACCEPT_NEGOTIATIONS,
        planet_id=planet.id,
        argument=from_planet.id,
    )
    refuse_neg = Action(
        action_type=ActionType.REFUSE_NEGOTIATIONS,
        planet_id=planet.id,
        argument=from_planet.id,
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='Принять', callback_data=get_action_data(accept_neg)
                ),
                InlineKeyboardButton(
                    text='Отклонить', callback_data=get_action_data(refuse_neg)
                ),
            ]
        ]
    )


def end_negotiations_keyboard(
    planet_to: PlanetDto, planet_from: PlanetDto
) -> InlineKeyboardMarkup:
    end_negotiations_order = Action(
        action_type=ActionType.END_NEGOTIATIONS,
        planet_id=planet_to.id,
        argument=planet_from.id,
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='Завершить переговоры',
                    callback_data=get_action_data(end_negotiations_order),
                )
            ]
        ]
    )


# Клавиатура выбора количества планет в игре
def number_of_planets_keyboard(pack: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(i), callback_data=f'{i},{pack}')
                for i in range(2, 6)
            ],
            [
                InlineKeyboardButton(text=str(i), callback_data=f'{i},{pack}')
                for i in range(6, 10)
            ],
        ]
    )


def ingame_keyboard(isadmin: bool, game: GameDto | None = None):
    if game is not None:
        if game.status in (GameStatus.ROUND, GameStatus.MEETING):
            return None
        elif game.status == GameStatus.ENDED and isadmin:
            return ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='Выйти из лобби')]]
            )
    if isadmin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Начать игру')],
                [KeyboardButton(text='Выйти из лобби')],
            ]
        )
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Выйти из лобби')]])



# Клавиатура выбора паков
def pack_keyboard():
    builder = InlineKeyboardBuilder()
    for pack in packs:
        builder.add(InlineKeyboardButton(text=pack.name, callback_data=pack.name))
    return builder.adjust(2).as_markup()


def request_keyboard(id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Принять', callback_data=f'accept_request {id}'),
                InlineKeyboardButton(text='Отклонить', callback_data=f'refuse_request {id}'),
            ]
        ]
    )


def round_stats_keyboard(game: GameDto, for_user: AdminDto) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='📊 Открыть статистику после раунда',
                    url=f'{WEB_APP_URL}/{game.id}/{game.round}?auth_token={sign_user_id(for_user.tg_id)}'
                )
            ]
        ]
    )

def get_reply_markup_keyboard(
    is_admin: bool, is_in_game: bool
) -> ReplyKeyboardMarkup:
    if is_in_game:
        return ingame_keyboard(is_admin)
    
    return start_keyboard(is_admin)
