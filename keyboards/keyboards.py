import json

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.schemas import CityDto, GameDto, PlanetDto
from game.config import game_config
from keyboards.schemas import Action, ActionType


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
    if nround == 1:
        for city in cities:
            str1 = '✅' if city.id in developed_ids else ''
            action = Action(
                action_type=ActionType.DEVELOP,
                planet_id=planet.id,
                argument=city.id,
            )
            builder.add(
                InlineKeyboardButton(
                    text=f'{str1}📈 {city.name} ({game_config.DEVELOPMENT_COST} 💵)',
                    callback_data=action.model_dump_json(),
                )
            )
        return builder.adjust(2).as_markup()
    
    for city in cities:
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
                callback_data=develop_action.model_dump_json(),
            ),
            InlineKeyboardButton(
                text=f'{str2}🛡️ {city.name} ({game_config.SHIELD_COST} 💵)',
                callback_data=shield_action.model_dump_json(),
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
        sanctions_action = Action(
            action_type=ActionType.SANCTIONS, planet_id=planet.id,
            argument=other_planet.id,
        )
        builder.add(
            InlineKeyboardButton(
                text=f'{addition}{other_planet.name}',
                callback_data=sanctions_action.model_dump_json(),
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
                    text=('✅ ' if chosen else '') + f'Разработать ({game_config.INVENTION_COST} 💵)',
                    callback_data=invent_action.model_dump_json(),
                )
            ]
        ]
    )


def meteorites_keyboard(planet: PlanetDto, chosen: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, game_config.MAX_METEORITES_TO_BUY):
        action = Action(
            action_type=ActionType.CREATE,
            planet_id=planet.id,
            argument=i, 
        )
        if chosen == i:
            builder.add(
                InlineKeyboardButton(
                    text=f'✅ {i} ({game_config.CREATE_COST * i} 💵)',
                    callback_data=action.model_dump_json(),
                )
            )
        else:
            builder.add(
                InlineKeyboardButton(
                    text=f'{i} ({game_config.CREATE_COST * i} 💵)',
                    callback_data=action.model_dump_json()
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
                    callback_data=action.model_dump_json(),
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
            attack_action = Action(
                action_type=ActionType.ATTACK,
                planet_id=planet.id,
                argument=city.id,
            )
            builder.add(
                InlineKeyboardButton(
                    text=f'{add}🗡 {city.name}',
                    callback_data=attack_action.model_dump_json(),
                )
            )
    negotiate_action = Action(
        action_type=ActionType.NEGOTIATE,
        planet_id=planet.id,
        argument=other_planet.id,
        
    )
    transaction_action = Action(
        action_type=ActionType.TRANSACTION,
        planet_id=planet.id
    )
    builder.add(
        InlineKeyboardButton(
            text='Переговоры 📞',
            callback_data=negotiate_action.model_dump_json(),
        ),
        InlineKeyboardButton(
            text='Перевод 💸',
            callback_data=transaction_action.model_dump_json(),
        ),
    )
    return builder.adjust(2).as_markup()


def negotiations_offer_keyboard(planet: PlanetDto, from_planet: PlanetDto):
    accept_neg = Action(
        action_type=ActionType.ACCEPT_NEGOTIATIONS,
        planet_id=planet.id, argument=from_planet.id
    )
    refuse_neg = Action(
        action_type=ActionType.REFUSE_NEGOTIATIONS,
        planet_id=planet.id, argument=from_planet.id
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='Принять', callback_data=accept_neg.model_dump_json()
                ),
                InlineKeyboardButton(
                    text='Отклонить', callback_data=refuse_neg.model_dump_json()
                ),
            ]
        ]
    )

def end_negotiations_keyboard(planet_to: PlanetDto, planet_from: PlanetDto) -> InlineKeyboardMarkup:
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
                    callback_data=end_negotiations_order.model_dump_json()
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

def round_stats_keyboard(game: GameDto) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            # TODO: make site for statistics
            InlineKeyboardButton(
                text='📊 Открыть статистику после раунда',
                web_app=WebAppInfo(url=f'https://some_url.com/{game.id}/{game.round}')
            )
        ]]
    )
