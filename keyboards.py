from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from game_classes import Game, City, Planet
import json
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

#Клавиатура админа в начале

def start_keyboard(isadmin: bool):
    if isadmin:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Создать игру')], 
                                             [KeyboardButton(text='Войти в игру')]])
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Войти в игру')]])

def choose_lobby_keyboard(games : list[Game]):
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.add(InlineKeyboardButton(text=str(game.id), callback_data=str(game.id)))
    return builder.adjust(4).as_markup()

#Клавиатура городов

def city_keyboard(nround: int, planet : Planet, cities: list[City], under_shield: list[City], developed: list[City]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if nround == 1:
        for city in cities:
            str1 = '✅' if city in developed else ''
            builder.add(InlineKeyboardButton(text=f'{str1}📈 {city.name()} (150 💵)', 
                                            callback_data=f'develop {planet.id} {city.id}'))
    else:
        for city in cities:
            str1, str2 = '', ''
            if city in developed:
                str1 = '✅'
            if city in under_shield:
                str2 = '✅'
            builder.add(InlineKeyboardButton(text=f'{str1}📈 {city.name()} (150 💵)', callback_data=f'develop {planet.id} {city.id}'), 
                        InlineKeyboardButton(text=f'{str2}🛡️ {city.name()} (300 💵)', callback_data=f'defend {planet.id} {city.id}'))
    return builder.adjust(2).as_markup()

def sanctions_keyboard(planet : Planet, planets: list[Planet], under_sanctions: list[Planet]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    planets.remove(planet)
    for other_planet in planets:
        addition = '✅ ' if other_planet in under_sanctions else ''
        other_name = morph.parse(other_planet.name())[0]
        other_name = other_name.inflect({'accs'}).word.capitalize()
        builder.add(InlineKeyboardButton(text=f'{addition}Наложить санкции на {other_name}', 
                                         callback_data=f'sanctions {planet.id} {other_planet.id}'))
    return builder.adjust(2).as_markup()

def invent_meteorites_keyboard(planet : Planet, chosen: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=('✅ ' if chosen else '') + 'Разработать (500 💵)', 
                                                      callback_data=f'invent {planet.id}')]])

def meteorites_keyboard(planet: Planet, chosen: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 4):
        if chosen == i:
            builder.add(InlineKeyboardButton(text=f'✅ Купить {i} ({150*i} 💵)', 
                                             callback_data=f'create {planet.id} {i}'))
        else:
            builder.add(InlineKeyboardButton(text=f'Купить {i} ({150*i} 💵)', 
                                             callback_data=f'create {planet.id} {i}'))
    return builder.adjust(3).as_markup()

def eco_keyboard(planet: Planet, chosen: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Отправить метеорит в аномалию' if chosen else 'Отправить метеорит в аномалию', 
                                callback_data=f'eco {planet.id}')]])

def other_planets_keyboard(nround: int, planet: Planet, other_planet: Planet, chosen_cities: list[City]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if nround > 1:
        for city in other_planet.cities():
            add = '✅ ' if city in chosen_cities else ''
            cityname = morph.parse(city.name())[0]
            cityname = cityname.inflect({'accs'}).word.capitalize()
            builder.add(InlineKeyboardButton(text=f'{add}Атаковать {cityname}', 
                                            callback_data=f'attack {planet.id} {city.id}'))
    builder.add(InlineKeyboardButton(text='Запросить переговоры 📞', 
                                     callback_data=f'negotiations {planet.id} {other_planet.id}'),
                InlineKeyboardButton(text='Перевести денег 💸', 
                                     callback_data=f'transaction {planet.id} {other_planet.id}'))
    return builder.adjust(2).as_markup()

def negotiations_offer_keyboard(planet : Planet, from_planet: Planet):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Принять', callback_data=f'accept {planet.id} {from_planet.id}'), 
                                                  InlineKeyboardButton(text='Отклонить', callback_data=f'deny {planet.id} {from_planet.id}')]])

end_negotiations_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Завершить переговоры',
                                           callback_data='end_negotiations')]])


#Клавиатура выбора количества планет в игре
def number_of_planets_keyboard(pack: str):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i), callback_data=f'{i},{pack}') for i in range(2, 6)],
                                                 [InlineKeyboardButton(text=str(i), callback_data=f'{i},{pack}') for i in range(6, 10)]])

#Клавиатура админа в игре
def ingame_keyboard(isadmin: bool):
    if isadmin:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Начать игру')],
                                             [KeyboardButton(text='Выйти из игры')]])
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Выйти из игры')]])

conversations_admin_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Начать следующий раунд')]])

#Клавиатура выбора паков
def pack_keyboard():
    file = open('./presets/planets_and_cities.json', encoding='utf-8')
    d = json.load(file)
    builder = InlineKeyboardBuilder()
    for key in d.keys():
        builder.add(InlineKeyboardButton(text=key, callback_data=key))
    return builder.adjust(2).as_markup()