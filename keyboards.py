from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from game_classes import Game, City, Planet

#Клавиатура админа в начале
start_admin_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Создать игру')], [KeyboardButton('Войти в игру')]])


#Клавиатура городов

def start_city_keyboard(cities: list[City], developed: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for city in cities:
        str1 = ' ✅' if city in developed else ''
        kb.add(InlineKeyboardButton(text=f'📈 {city.name()} (150 💵){str1}', callback_data=f'develop {city.name()}'))
    return kb

def city_keyboard(cities: list[City], under_shield: list[City], developed: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for city in cities:
        str1, str2 = '', ''
        if city in developed:
            str1 = ' ✅'
        if city in under_shield:
            str2 = ' ✅'
        kb.add(InlineKeyboardButton(text=f'📈 {city.name()} (150 💵){str1}', callback_data=f'develop {city.name()}'), InlineKeyboardButton(text=f'🛡️ {city.name()} (300 💵){str2} ', callback_data=f'defend {city.name()}'))
    return kb

def sanctions_keyboard(planets: list[str], under_sanctions: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for planet in planets:
        if planet in under_sanctions:
            kb.add(InlineKeyboardButton(text=f'Наложить санкции на {planet} ✅', callback_data=f'sanctions {planet}'))
        else:
            kb.add(InlineKeyboardButton(text=f'Наложить санкции на {planet}', callback_data=f'sanctions {planet}'))
    return kb

def invent_meteorites_keyboard(chosen: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(text='Разработать (500 💵)' + (' ✅' if chosen else ''), callback_data='invent'))

def meteorites_keyboard(chosen: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    for i in range(1, 4):
        if chosen == i:
            kb.add(InlineKeyboardButton(text=f'{i} ({150*i} 💵) ✅', callback_data=f'create 0'))
        else:
            kb.add(InlineKeyboardButton(text=f'{i} ({150*i} 💵)', callback_data=f'create {i}'))
    return kb

def eco_keyboard(chosen: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('Отправить метеорит в аномалию ✅' if chosen else 'Отправить метеорит в аномалию', callback_data='eco'))
    return kb

def other_planets_keyboard(planet: Planet, chosen_cities: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for city in planet.cities():
        if city.development() > 0:
            if city in chosen_cities:
                kb.add(InlineKeyboardButton(text=f'Атаковать {city.name()} ✅', callback_data=f'attack {city.name()}'))
            else:
                kb.add(InlineKeyboardButton(text=f'Атаковать {city.name()}', callback_data=f'attack {city.name()}'))
    kb.add(InlineKeyboardButton(text='Запросить переговоры 📞', callback_data=f'conversations {planet.name()}'))
    kb.add(InlineKeyboardButton(text='Перевести денег 💸', callback_data=f'transaction {planet.name()}'))
    return kb

def negotiations_offer_keyboard(from_planet: Planet):
    return InlineKeyboardMarkup().add(InlineKeyboardButton('Принять', callback_data=f'accept {from_planet.name()}'), 
                                      InlineKeyboardButton('Отклонить', callback_data=f'deny {from_planet.name()}'))

end_conversations_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton('Завершить переговоры', callback_data='end_negotiations'))

#Клавиатура пользователя в игре
main_player_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Аттака ☄️'), KeyboardButton('Защита 🛡️'), KeyboardButton('Переговоры 📞')],
                                       [KeyboardButton('Развитие 📈'), KeyboardButton('Санкции 📃'), KeyboardButton('Транзакция 💸')],
                                       [KeyboardButton('Баланс 💰'), KeyboardButton('Отмена действий ❌'), KeyboardButton('Справка ❓')]])

start_player_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Развитие 📈'), KeyboardButton('Баланс 💰')],
                                             [KeyboardButton('Разработка ☄️'), KeyboardButton('Отмена действий ❌')],
                                             [KeyboardButton('Справка ❓')]])

peaceful_player_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Разработка ☄️'), KeyboardButton('Защита 🛡️'), KeyboardButton('Переговоры 📞')],
                                       [KeyboardButton('Развитие 📈'), KeyboardButton('Санкции 📃'), KeyboardButton('Транзакция 💸')],
                                       [KeyboardButton('Баланс 💰'), KeyboardButton('Отмена действий ❌'), KeyboardButton('Справка ❓')]])

#Клавиатура выбора количества планет в игре
number_of_planets_keyboard = InlineKeyboardMarkup(row_width=5)
number_of_planets_keyboard.add(*[InlineKeyboardButton(text=str(i), callback_data=str(i)) for i in range(2, 7)])

#Клавиатура админа в игре
ingame_admin_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Начать игру')], [KeyboardButton('Выйти из игры')]])
conversations_admin_keyboard = ReplyKeyboardMarkup([[KeyboardButton('Начать следующий раунд')]])