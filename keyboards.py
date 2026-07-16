import json

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.schemas import CityDto, PlanetDto
from game.config import game_config


# Клавиатура админа в начале


def start_keyboard(isadmin: bool):
    if isadmin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Создать игру')],
                [KeyboardButton(text='Войти в игру')],
            ]
        )
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Войти в игру')]])


def choose_lobby_keyboard(games: list[Game]):
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
    if nround == 1:
        for city in cities:
            str1 = '✅' if city.id in developed_ids else ''
            builder.add(
                InlineKeyboardButton(
                    text=f'{str1}📈 {city.name} ({game_config.DEVELOPMENT_COST} 💵)',
                    callback_data=f'develop {planet.id} {city.id}',
                )
            )
        return builder.adjust(2).as_markup()
    
    for city in cities:
        str1, str2 = '', ''
        if city.id in developed_ids:
            str1 = '✅'
        if city.id in under_shield_ids:
            str2 = '✅'
        builder.add(
            InlineKeyboardButton(
                text=f'{str1}📈 {city.name} ({game_config.DEVELOPMENT_COST} 💵)',
                callback_data=f'develop {planet.id} {city.id}',
            ),
            InlineKeyboardButton(
                text=f'{str2}🛡️ {city.name} ({game_config.SHIELD_COST} 💵)',
                callback_data=f'defend {planet.id} {city.id}',
            ),
        )
    return builder.adjust(2).as_markup()


def sanctions_keyboard(
    planet: PlanetDto,
    other_planets: list[PlanetDto],
    under_sanctions_ids: list[int]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for other_planet in other_planets:
        addition = '✅ ' if other_planet.id in under_sanctions_ids else ''
        builder.add(
            InlineKeyboardButton(
                text=f'{addition}{other_planet.name}',
                callback_data=f'sanctions {planet.id} {other_planet.id}',
            )
        )
    return builder.adjust(2).as_markup()


def invent_meteorites_keyboard(planet: PlanetDto, chosen: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=('✅ ' if chosen else '') + f'Разработать ({game_config.INVENTION_COST} 💵)',
                    callback_data=f'invent {planet.id}',
                )
            ]
        ]
    )


def meteorites_keyboard(planet: PlanetDto, chosen: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, game_config.MAX_METEORITES_TO_BUY):
        if chosen == i:
            builder.add(
                InlineKeyboardButton(
                    text=f'✅ {i} ({game_config.CREATE_COST * i} 💵)',
                    callback_data=f'create {planet.id} {i}',
                )
            )
        else:
            builder.add(
                InlineKeyboardButton(
                    text=f'{i} ({game_config.CREATE_COST * i} 💵)',
                    callback_data=f'create {planet.id} {i}'
                )
            )
    return builder.adjust(3).as_markup()


def eco_keyboard(planet: PlanetDto, chosen: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✅ Отправить метеорит в аномалию'
                    if chosen
                    else 'Отправить метеорит в аномалию',
                    callback_data=f'eco {planet.id}',
                )
            ]
        ]
    )


def other_planets_keyboard(
    nround: int,
    planet: PlanetDto,
    other_planet: PlanetDto,
    other_cities: list[CityDto],
    attacked_cities_ids: list[int]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if nround > 1:
        for city in other_cities:
            add = '✅ ' if city.id in attacked_cities_ids else ''
            builder.add(
                InlineKeyboardButton(
                    text=f'{add}🗡 {city.name}',
                    callback_data=f'attack {planet.id} {city.id}',
                )
            )
    builder.add(
        InlineKeyboardButton(
            text='Переговоры 📞',
            callback_data=f'negotiations {planet.id} {other_planet.id}',
        ),
        InlineKeyboardButton(
            text='Перевод 💸',
            callback_data=f'transaction {planet.id} {other_planet.id}',
        ),
    )
    return builder.adjust(2).as_markup()


def negotiations_offer_keyboard(planet: PlanetDto, from_planet: PlanetDto):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='Принять', callback_data=f'accept {planet.id} {from_planet.id}'
                ),
                InlineKeyboardButton(
                    text='Отклонить', callback_data=f'deny {planet.id} {from_planet.id}'
                ),
            ]
        ]
    )


end_negotiations_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Завершить переговоры', callback_data='end_negotiations'
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


# Клавиатура админа в игре
def ingame_keyboard(isadmin: bool):
    if isadmin:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Начать игру')],
                [KeyboardButton(text='Выйти из игры')],
            ]
        )
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Выйти из игры')]])


conversations_admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Начать следующий раунд')]]
)


# Клавиатура выбора паков
def pack_keyboard():
    file = open('./presets/planets_and_cities.json', encoding='utf-8')
    d = json.load(file)
    builder = InlineKeyboardBuilder()
    for key in d.keys():
        builder.add(InlineKeyboardButton(text=key, callback_data=key))
    return builder.adjust(2).as_markup()


def request_keyboard(id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Принять', callback_data=f'knight {id}'),
                InlineKeyboardButton(text='Отклонить', callback_data=f'notknight {id}'),
            ]
        ]
    )
