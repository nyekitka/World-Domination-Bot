import logging
from aiogram import Dispatcher, executor, Bot, types
from aiogram.types import InputFile
from aiogram.dispatcher import FSMContext
from keyboards import *
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from random import shuffle
import asyncio, pymorphy3, os
from zipfile import ZipFile

class BotStates(StatesGroup):
    planets_numbers = State()
    entering_game = State()
    choosing_city_to_develop = State()
    
    

BOT_TOKEN = '6300949258:AAH58zEGG1WSAwjrRdUEVVM21LgsVlVmcKg'
morph = pymorphy3.MorphAnalyzer()
logging.basicConfig(level=logging.INFO)

Messages = {
    'start' : 'Привет 👋. Для того, чтобы войти используйте команду /login <логин>',
    'login' : 'Добро пожаловать, {0}!',
    'already_logged' : 'Вы уже вошли в систему. Сначала выйдите с помощью /exit, затем войдите с помощью /login.',
    'login_failure' : 'Такого пользователя не существует. Введите свой логин заново с помощью /login <логин>',
    'login_online' : 'Такой пользователь уже в сети. Войдите под другим логином.',
    'entering_game_admin' : 'Вы присоединились к игре {0}. Теперь вам доступна панель администрации игры, а также вся информация о ней',
    'entering_game_user' : 'Команда от планеты {0} присоединилась к нам! В игре: {1}/{2}.',
    'starting_game_not_being_in' : 'Вы не неходитесь ни в какой в игре. Сначала войдите в игру!',
    'not_enough_players' : 'Недостаточно игроков в игре ({0}/{1} 👤 присоединилось). Подождите пока войдут все, а затем начинайте игру',
    'on_user_joined' : 'Представитель планеты {0} присоединился к игре ({1}/{2} 👤)',
    'on_user_left' : 'Представитель планеты {0} вышел из игры ({1}/{2} 👤)',
    'signout' : 'Вы вышли из игры. Чтобы войти заново, используйте команду /login',
    '5 minutes left' : 'Внимание, до конца раунда осталось 5 минут ⏳. Не забывайте заполнить свои приказы.',
    '1 minute left' : 'Внимание, до конца раунда осталась 1 минута ⌛. Если ещё не заполнили свои приказы, то самое время это сделать, иначе приказы отправятся пустыми.',
    'first_round' : """*Первый раунд начался*
В течение этого раунда вы должны обсудить в команде свою стратегию на игру\\. 
Также вы уже можете вложить деньги в разработку технологии отправки метеоритов \\(Разработка ☄️\\) для последующей атаки аномалии или чужих городов либо же вложить их в развитие собственных городов \\(Развитие 📈\\)\\.""",
    'city_info': """*{0}*
*Доступный бюджет:* _{1}_ 💵
*Средний уровень жизни на планете:* _{2}%_
*Города:*
_{3}_\t\\(Развитие: _{4} %_; Уровень жизни: _{5} %_; Доход: _{6}_ 💵\\)
_{7}_\t\\(Развитие: _{8} %_; Уровень жизни: _{9} %_; Доход: _{10}_ 💵\\)
_{11}_\t\\(Развитие: _{12} %_; Уровень жизни: _{13} %_; Доход: _{14}_ 💵\\)
_{15}_\t\\(Развитие: _{16} %_; Уровень жизни: _{17} %_; Доход: _{18}_ 💵\\)""",
    'sanctions_info' : "*Санкции:*\n_{0}_",
    'eco_info' : '*Венерианская аномалия*\nУровень аномалии: _{0} %_',
    'other_planet' : """"*{0}*
{1}\t\\(Развитие: _{2} %_\\)
{3}\t\\(Развитие: _{4} %_\\)
{5}\t\\(Развитие: _{6} %_\\)
{7}\t\\(Развитие: _{8} %_\\)""",
    'no_enough_money' : 'У вас недостаточно средств для выполнения этого действия. Отмените предыдущие и попробуйте заново.',
    'round_results' : '{0} раунд закончен!\nВ следующем архиве представлены результаты раунда. Откройте в архиве html-файл.',
    'end_of_round' : '_*{0} раунд закончен\\!*_\nОтправляйтесь на межпланетные переговоры, чтобы увидеть результаты раунда и обсудить их\\.'
}

common_users = dict()   #обычные пользователи
users_online = dict()   #пользователи онлайн (ключ - логин, значение - id пользователя)
admins = []             #список админов
admin_ids = set()       #айдишники админов
available_logins = []   #оставшиеся логины
games = []              #созданные игры: список списков, каждый список: [игра, список админов игры (их айдишников), словарь: планета -> словарь с информацией для бота]

with open('admins.txt', 'r') as file:
    admins = [line.strip() for line in file]
with open('logins.txt', 'r') as file:
    available_logins = [line.strip() for line in file]
shuffle(available_logins)
    
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

############################################ Вспомогательные функции ##################################################

def html_page_generator(gameid: int, game: Game):
    os.chdir("round results")
    file = open(f'results_{gameid}{game.show_round()}.html', 'w', encoding='UTF-8')
    with open('presets\\head.txt', encoding='UTF-8') as head:
        file.write(''.join(head.readlines()).format(gameid))
    i = 1
    for planet in game.planets().values():
        cities = planet.cities()
        names_of_cities = [c.name() for c in cities]
        percentages = [c.rate_of_life(game.eco_rate) for c in cities]
        s = None
        with open('presets\\planet panel.txt', encoding='UTF-8') as panel:
            s = ''.join(panel.readlines())
            args = [planet.name(), i]
            for j in range(len(names_of_cities)):
                args.extend(
                    ['', names_of_cities[j]] if percentages[j] != 0 else ['dead-', f'<s>{names_of_cities[j]}</s>'])
            for j in range(len(names_of_cities)):
                args.extend(['dead-' if percentages[j] == 0 else '', percentages[j]])
            s = s.format(*args)
            file.write(s)
        i += 1
    with open('presets\\chart begin preset.txt', encoding='UTF-8') as chart:
        file.write(''.join(chart.readlines()))
    rates_of_life = [planet.rate_of_life() for planet in game.planets().values()]
    max_rate = max(rates_of_life)
    planets = list(game.planets().keys())
    bar_preset = None
    with open('presets\\bar preset.txt', encoding='UTF-8') as bar:
        bar_preset = ''.join(bar.readlines())
    for j in range(len(planets)):
        file.write(bar_preset.format(rates_of_life[j] / 100 * max_rate, rates_of_life[j], planets[j]))
    with open('presets\\ending preset.txt', encoding='UTF-8') as end:
        file.write(''.join(end.readlines()).format(100 - game.eco_rate))
    file.close()
    os.chdir("..")

def css_generator(gameid: int, n: int):
    colors = ('green', 'red', 'blue', 'orange', 'purple', 'yellowgreen', 'darkred', 'darkblue')
    os.chdir("round results")
    file = open(f'style{gameid}.css', 'w', encoding='UTF-8')
    preset = open(f'presets\\style.css', 'r', encoding='UTF-8')
    file.write(''.join(preset.readlines()))
    preset.close()
    file.write('.panel-1')
    for i in range(2, n + 1):
        file.write(f', .panel-{i}')
    with open('presets\\panel settings.txt') as sets:
        file.write(''.join(sets.readlines()))
    file.write('.upper-half-1')
    for i in range(2, n + 1):
        file.write(f', .upper-half-{i}')
    with open('presets\\upper-half settings.txt') as sets:
        file.write(''.join(sets.readlines()))
    for i in range(n):
        file.write(f""".upper-half-{i + 1} {{
    background-color: {colors[i]};
}}\n\n""")
    file.close()
    os.chdir("..")
        

async def timer(n: int):
    await asyncio.sleep(10)
    for user in games[n][0].active_users():
        await bot.send_message(users_online[user], Messages['5 minutes left'])
    for user in games[n][1]:
        await bot.send_message(user, Messages['5 minutes left'])
    await asyncio.sleep(10)
    for user in games[n][0].active_users():
        await bot.send_message(users_online[user], Messages['1 minute left'])
    for user in games[n][1]:
        await bot.send_message(user, Messages['1 minute left'])
    await asyncio.sleep(10)
    games[n][0].end_this_round()
    round = games[n][0].show_round()
    for user in games[n][0].active_users():
        await bot.send_message(users_online[user], Messages['end_of_round'].format(round), 'MarkdownV2')
    if round == 1:
        css_generator(n, games[n][0].number_of_planets())
    html_page_generator(n, games[n][0])
    os.chdir("round results")
    with ZipFile(f'{n + 1} game {round} round results.zip', 'w') as zfile:
        zfile.write(f'style{n}.css')
        zfile.write(f'results_{n}{round}.html')
        for file in os.listdir('fonts'):
            zfile.write(f'fonts\\{file}')
    for admin in games[n][1]:
        await bot.send_document(admin, 
                                InputFile(f'{n + 1} game {round} round results.zip'),
                                caption=Messages['round_results'].format(round),
                                reply_markup=conversations_admin_keyboard)
    os.chdir('..')
        

def city_stats_message(planet: Planet) -> str:
    all_info = [planet.name(),
                planet.balance(),
                planet.rate_of_life()]
    cities = planet.cities()
    for city in cities:
        addition = ''
        if city.is_under_shield():
            addition = ' 🛡️'
        elif city.development() == 0:
            addition = ' ❌'
        all_info.extend([city.name() + addition, city.development(), city.rate_of_life(planet.game().eco_rate), city.income()])
    return Messages['city_info'].format(*all_info)

def sanctions_message(planet: Planet) -> str:
    sanctions = planet.show_sanc_set()
    if len(sanctions) == 0:
        return Messages['sanctions_info'].format('Ни одна из планет не наложила на вас санкции')
    else:
        return Messages['sanctions_info'].format(', '.join(sanctions))

def meteorites_message(planet: Planet) -> str:
    if planet.is_invented():
        word = morph.parse('метеорит')[0]
        word = word.make_agree_with_number(planet.meteorites_count()).word
        return f'*Метеориты:*\n_У вас {planet.meteorites_count()} {word}_ ☄️'
    else:
        return '*Метеориты:*\n_У вас не разработана технология отправки метеоритов_'

def eco_message(game: Game) -> str:
    return Messages['eco_info'].format(game.eco_rate)

def other_planets_message(planet: Planet) -> str:
    args = [planet.name()]
    for city in planet.cities():
        args.extend([city.name() + ' ❌' if city.development() == 0 else '', city.development()])
    return Messages['other_planet'].format(args)
        

def gameid_by_login(login: str) -> int:
    for i in range(len(games)):
        ans = games[i][0].get_homeland(login)
        if ans is not None:
            return i

async def method_executor(method, id : int, *args):
    try:
        method(*args)
    except ArithmeticError:
        await bot.answer_callback_query(id, Messages['no_enough_money'], True)
        return False
    return True
        
    
############################################### Команды вне игры #######################################################

@dp.message_handler(commands=['start'])
async def start(message : types.Message):
    await message.answer(Messages['start'])

@dp.message_handler(commands=['login'])
async def intializer(message: types.Message):
    login = message.get_args()
    if message.from_id in users_online.values():
        if message.from_id in admin_ids:
            await message.answer(Messages['already_logged'], reply_markup=start_admin_keyboard)
        else:
            await message.answer(Messages['already_logged'])
    elif login not in admins and login not in common_users.keys():
        await message.answer(Messages['login_failure'])
    elif login in users_online.keys():
        await message.answer(Messages['login_online'])
    elif login in common_users.keys():
        users_online[login] = message.from_id
        gameid = gameid_by_login(login)
        game = games[gameid][0]
        planet = game.get_homeland(login)
        active_players = game.active_users()
        game.join_user(login)
        for user in active_players:
            await bot.send_message(chat_id=users_online[user], text=Messages['on_user_joined'].format(planet.name(), game.users_online(), game.number_of_planets()))
        for user in games[gameid][1]:
            await bot.send_message(chat_id=user, text=Messages['on_user_joined'].format(planet.name(), game.users_online(), game.number_of_planets()))
        await message.answer(Messages['login'].format(login))
    else:
        users_online[login] = message.from_id
        admin_ids.add(message.from_id)
        await message.answer(text=Messages['login'].format(login), reply_markup=start_admin_keyboard)

@dp.message_handler(commands=['signout'])
async def signout(message : types.Message):
    id = message.from_id
    login_ = None
    for login, uid in users_online.items():
        if uid == id:
            login_ = login
            users_online.pop(login)
            break
    if id in admin_ids:
        admin_ids.remove(id)
        for gid in range(len(games)):
            if id in games[gid][1]:
                games[gid][1].remove(id)
    else:
        gameid = gameid_by_login(login_)
        game = games[gameid][0]
        planet = game.get_homeland(login_)
        game.kick_user(login_)
        active_players = game.active_users()
        for user in active_players:
            await bot.send_message(chat_id=users_online[user], text=Messages['on_user_left'].format(planet.name(), game.users_online(), game.number_of_planets()))
        for user in games[gameid][1]:
            await bot.send_message(chat_id=user, text=Messages['on_user_left'].format(planet.name(), game.users_online(), game.number_of_planets()))
    await message.answer(Messages['signout'])

@dp.message_handler(commands=['rules'])
async def rules(message : types.Message):
    with open('rules.txt', 'r', encoding='UTF-8') as file:
        text = ''.join(file.readlines())
        await message.answer(text=text, parse_mode='MarkdownV2')

############################################# Кнопочные команды вне игры #################################################

@dp.message_handler(lambda message: message.text == 'Создать игру' and message.from_id in admin_ids)
async def create_game(message : types.Message):
    await message.answer('Выберите количество планет в игре', reply_markup=number_of_planets_keyboard)
    await BotStates.planets_numbers.set()
    
@dp.message_handler(lambda message: message.text == 'Войти в игру' and message.from_id in admin_ids)
async def enter_game(message : types.Message):
    markup = InlineKeyboardMarkup(row_width=len(games))
    markup.add(*[InlineKeyboardButton(text=str(i), callback_data=str(i)) for i in range(1, len(games) + 1)])
    await message.answer('Выберите игру, к которой хотите присоединиться', reply_markup=markup)
    await BotStates.entering_game.set()

@dp.message_handler(lambda message: message.text == 'Выйти из игры' and message.from_id in admin_ids)
async def leave_game(message: types.Message):
    for i in range(len(games)):
        if message.from_id in games[i][1]:
            games[i][1].remove(message.from_id)
            await message.answer(f'Вы вышли из игры {i + 1}.', reply_markup=start_admin_keyboard)
            break

@dp.message_handler(lambda message: message.text == 'Начать игру' and message.from_id in admin_ids)
async def start_game(message : types.Message):
    game_id = None
    for i in range(len(games)):
        if message.from_id in games[i][1]:
            game_id = i
            break
    else:
        await message.answer(Messages['starting_game_not_being_in'], reply_markup=start_admin_keyboard)
        return
    game = games[game_id][0]
    
    if game.users_online() < game.number_of_planets():
        await message.answer(Messages['not_enough_players'].format(game.users_online(), game.number_of_planets()), reply_markup=ingame_admin_keyboard)
    else:
        game.start_new_round()
        games[game_id].append(dict())
        for user in game.all_users():
            planet = game.get_homeland(user)
            await bot.send_message(users_online[user], Messages['first_round'], parse_mode='MarkdownV2')
            games[game_id][2][planet] = dict()
            games[game_id][2][planet]['city_info'] = await bot.send_message(users_online[user], city_stats_message(planet), reply_markup=start_city_keyboard(planet.cities(), []), parse_mode='MarkdownV2')
            games[game_id][2][planet]['meteorites_info'] = await bot.send_message(users_online[user], meteorites_message(planet), reply_markup=invent_meteorites_keyboard(False), parse_mode='MarkdownV2')
        await timer(game_id)
    
@dp.callback_query_handler(state=BotStates.planets_numbers)
async def set_number_of_planets(call: types.CallbackQuery, state: FSMContext):
    global available_logins
    number = int(call.data)
    game_logins = available_logins[-number:]
    available_logins = available_logins[:-number]
    games.append([Game(number, game_logins), []])
    planets = games[-1][0].info()
    message_text = f'Игра {len(games)} на {number} человек успешно создана\\!\nВот логины для входа:\n'
    for planet in planets.keys():
        if planet != 'eco_rate':
            login = games[-1][0].info(planet)['login']
            common_users[login] = (len(games) - 1, planet)
            message_text += f'{login} \\- _{planet}_\n'
    await call.message.answer(text=message_text, parse_mode='MarkdownV2')
    await state.finish()

@dp.callback_query_handler(state= BotStates.entering_game)
async def choose_lobby(call: types.CallbackQuery, state: FSMContext):
    number = int(call.data)
    games[number - 1][1].append(call.from_user.id)
    await call.message.answer(Messages['entering_game_admin'].format(number), reply_markup=ingame_admin_keyboard)
    await state.finish()


################################################# Внутриигровые команды ###################################################

@dp.callback_query_handler()
async def ingame_action(call: types.CallbackQuery):
    print('Начало функции')
    message = call.message
    id = call.from_user.id
    login = None
    for ulog, uid in users_online.items():
        if id == uid:
            login = ulog
            break
    print('Извлекли логин')
    gid = gameid_by_login(login)
    planet = games[gid][0].get_homeland(login)
    type_message = None
    for tp, msg in games[gid][2][planet].items():
        if msg == message:
            type_message = tp
            break
    print('Извлекли тип сообщения')
    if type_message == 'city_info':
        print('Это city_info')
        command, city_name = call.data.split()
        city = None
        for c in planet.cities():
            if c.name() == city_name:
                city = c
                break
        print('Нашли город')
        if command == 'develop':
            print('Это develop')
            res = await method_executor(planet.develop_city, call.id, city)
            if not res: return
        else:
            print('Это defend')
            res = await method_executor(planet.build_shield, call.id, city)
            if not res: return
    elif type_message == 'meteorites_info':
        print('Это meteorites_info')
        if call.data == 'invent':
            print('Это invent')
            res = await method_executor(planet.invent, call.id)
            if not res: return
            games[gid][2][planet]['meteorites_info'] = await bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=invent_meteorites_keyboard(planet.order()['invent']))
        else:
            n = int(call.data[-1])
            res = await method_executor(planet.create_meteorites, call.id, n)
            if not res: return
            games[gid][2][planet]['meteorites_info'] = await message.edit_text(meteorites_message(planet), 'MarkdownV2', reply_markup=meteorites_keyboard(n))
    print('Конечная хуйня')
    cities = [c for c in planet.cities() if c.development() != 0]
    developed = planet.order().get('develop', [])
    us = planet.order().get('build_shield', [])
    new_msg = city_stats_message(planet)
    if new_msg == games[gid][2][planet]['city_info'].text:
        if games[gid][0].show_round() == 1:
            games[gid][2][planet]['city_info'] = await games[gid][2][planet]['city_info'].edit_message_reply_markup(message.chat.id, games[gid][2][planet]['city_info'].id, reply_markup=start_city_keyboard(cities, developed))
        else:
            games[gid][2][planet]['city_info'] = await games[gid][2][planet]['city_info'].edit_message_reply_markup(message.chat.id, games[gid][2][planet]['city_info'].id, reply_markup=city_keyboard(cities, us, developed))
    else:
        if games[gid][0].show_round() == 1:
            games[gid][2][planet]['city_info'] = await games[gid][2][planet]['city_info'].edit_text(new_msg, parse_mode='MarkdownV2', reply_markup=start_city_keyboard(cities, developed))
        else:
            games[gid][2][planet]['city_info'] = await games[gid][2][planet]['city_info'].edit_text(new_msg, parse_mode='MarkdownV2', reply_markup=city_keyboard(cities, us, developed))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)