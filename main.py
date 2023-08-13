from aiogram import Dispatcher, executor, Bot, types
from aiogram.types import InputFile
from aiogram.dispatcher import FSMContext
from keyboards import *
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from random import shuffle
from num2words import num2words
import asyncio, pymorphy3, os, logging
from zipfile import ZipFile
import numpy as np
import pandas as pd
from game_classes import AlreadyBuiltShield, NotEnoughMoney, NotEnoughRockets, BusyAtTheMoment, BilateralNegotiations, NegotiationsOutside

class BotStates(StatesGroup):
    planets_numbers = State()
    entering_game = State()
    choosing_city_to_develop = State()
    transaction_state = State()
    
    

BOT_TOKEN = '6300949258:AAH58zEGG1WSAwjrRdUEVVM21LgsVlVmcKg'
morph = pymorphy3.MorphAnalyzer()
logging.basicConfig(level=logging.INFO)

Messages = {
    'start' : 'Привет 👋. Для того, чтобы войти используйте команду /login <логин>',
    'login' : 'Добро пожаловать, {0}!',
    'already_logged' : 'Вы уже вошли в систему. Сначала выйдите с помощью /signout, затем войдите с помощью /login.',
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
Также вы уже можете вложить деньги в разработку технологии отправки метеоритов для последующей атаки аномалии или чужих городов, либо же вложить их в развитие собственных городов \\(Развитие 📈\\)\\.""",
    'common_round' : """*{0} раунд начался*
У вас есть 10 минут, чтобы обсудить действия в этом раунде как внутри своей команды, так и с другими командами на переговорах\\. Не забывайте заполнять приказ\\!
""",
    'first_round_for_admins': '*Первый раунд начался*',
    'round_for_admins': '*{0} раунд начался*\n\nВам будут приходить запросы на переговоры от игроков\\. Как только придёт запрос, направляйтесь к команде, отправившей запрос и сопроводите дипломата до другой команды\\.',
    'city_info': """__*{0}*__

*Доступный бюджет:* _{1}_ 💵
*Сред\\. ур\\. жизни на планете:* _{2}%_

*{3}*
\\(Развитие: _{4} %_; Ур\\. жизни: _{5} %_; Доход: _{6}_ 💵\\)

*{7}*
\\(Развитие: _{8} %_; Ур\\. жизни: _{9} %_; Доход: _{10}_ 💵\\)

*{11}*
\\(Развитие: _{12} %_; Ур\\. жизни: _{13} %_; Доход: _{14}_ 💵\\)

*{15}*
\\(Развитие: _{16} %_; Ур\\. жизни: _{17} %_; Доход: _{18}_ 💵\\)""",
    'sanctions_info' : "*Санкции:*\n_{0}_",
    'eco_info' : '*Венерианская аномалия*\nУровень аномалии 💥: _{0} %_',
    'other_planet' : """__*{0}*__

{1}\t\\(Развитие: _{2} %_\\)
{3}\t\\(Развитие: _{4} %_\\)
{5}\t\\(Развитие: _{6} %_\\)
{7}\t\\(Развитие: _{8} %_\\)""",
    'not_enough_money' : 'У вас недостаточно средств для выполнения этого действия. Отмените предыдущие и попробуйте заново.',
    'not_enough_rockets' : 'У вас недостаточно метеоритов для этого действия. Отмените предыдущие действия или закупите метеориты.',
    'not_enough_for_transaction' : 'У вас недостаточно средств для перевода. Введите меньшую сумму для перевода или 0 для отмены перевода.',
    'wrong_answer' : 'Неверный ввод. Введите неотрицательное число, обозначающее сумму, которую вы хотите перевести планете.',
    'successful_transaction' : 'Перевод планете {0} успешно выполнен!',
    'transaction_notification' : 'Планета {0} перевела вам {1} 💵!',
    'already_built' : 'Вы не можете поставить щит на этот город, т.к. щит на этом городе уже поставлен.',
    'round_results' : '{0} раунд закончен!\nВ следующем архиве представлены результаты раунда. Откройте в архиве html-файл.',
    'game_results' : 'Статистика всей игры',
    'end_of_round' : '_*{0} раунд закончен\\!*_\nОтправляйтесь на межпланетные переговоры, чтобы увидеть результаты раунда и обсудить их\\.',
    'how_much_money' : 'Напишите сколько вы готовы перевести планете {0}.',
    'negotiations_offer' : 'Планета {0} предлагает принять их дипломата для переговоров.',
    'negotiations_accepted' : 'Планета {0} приняла ваше предложение о переговорах! Ждите организатора, который подойдёт к вам для того, чтобы сопроводить дипломата.',
    'negotiations_denied' : 'Планета {0} отказалась от вашего предложения о переговорах.',
    'wait_for_diplomatist' : 'Вы приняли предложение о переговорах с {0}. Ожидайте дипломата. Как только закончите переговоры, нажмите кнопку снизу.',
    'negotiations_for_admin' : 'Планета {0} хочет принять дипломата от планеты {1}',
    'negotiations_outside_the_round' : 'Вы не можете принять дипломата, т.к. находитесь на галактических переговорах.',
    'negotiations_ended' : 'Переговоры закончены. Ожидайте организатора, который сопроводит дипломата до его планеты.',
    'negotiations_ended_for_admin' : 'Планета {0} закончила переговоры. Сопроводите дипломата до его планеты.',
    'busy_at_the_moment' : 'Вы не можете принять к себе дипломата, т.к. на вашей планете уже ведутся переговоры.',
    'bilateral_negotiations' : 'Вы не можете принять к себе эту планету, т.к. дипломат от вашей планеты уже переговаривает с ней',
    'wait_for_acception' : 'Запрос на переговоры отправлен! Как только {0} примет решение, вам придёт сообщение.',
    'end_of_the_game' : '*Игра закончена\\!*\nОтправляйтесь на собрание, чтобы увидеть результаты игры\\.',
    'goodbye' : 'Вы автоматически вышли, т.к. ваша игра закончилась.',
    'ending_outside' : 'Вы не можете закончить никакую игру, т.к. не находитесь ни в одной из них.',
    'ending_when_not_started' : 'Вы не можете закончить неначавшуюся игру.',
    'game_interrupted_report' : 'Игра была прервана. Вы автоматически вышли из игры.',
    'game_interrupted_message' : 'Игра была прервана администратором. О подробностях узнавайте у организаторов.'
}

common_users = dict()   #обычные пользователи
users_online = dict()   #пользователи онлайн (ключ - логин, значение - id пользователя)
admins = []             #список админов
admin_ids = set()       #айдишники админов
available_logins = []   #оставшиеся логины
games = []              #созданные игры: список списков, каждый список: [игра, список админов игры (их айдишников), словарь: планета -> словарь с информацией для бота]
writers = []            #для того, чтобы сохранять в эксель

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
        file.write(bar_preset.format(rates_of_life[j] * 100 / max_rate, rates_of_life[j], planets[j]))
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
        
async def timer(n: int, secs: int = 600):
    global games, writers, common_users, available_logins
    await asyncio.sleep(secs // 2)
    if not games or games[n][0] is None:
        return
    for user in games[n][0].active_users():
        await bot.send_message(users_online[user], Messages['5 minutes left'])
    for user in games[n][1]:
        await bot.send_message(user, Messages['5 minutes left'])
    await asyncio.sleep(secs // 2 - secs // 10)
    if not games or games[n][0] is None:
        return
    for user in games[n][0].active_users():
        await bot.send_message(users_online[user], Messages['1 minute left'])
    for user in games[n][1]:
        await bot.send_message(user, Messages['1 minute left'])
    await asyncio.sleep(secs // 10)
    if not games or games[n][0] is None:
        return
    table = pd.DataFrame(columns=games[n][0].planets().keys(), index=['Развить города', 'Построить щит над', 'Изобрести технологию отправки метеоритов', 'Закупить метеориты', 'Отправить метеорит в аномалию', 'Наложить санкции на', 'Аттаковать'])
    for planet in games[n][0].planets().values():
        order = planet.order()
        if 'develop' in order.keys():
            table.loc['Развить города', planet.name()] = ','.join([c.name() for c in order['develop']])
        if 'sanctions' in order.keys():
            table.loc['Наложить санкции на', planet.name()] = ','.join(order['sanctions'])
        if 'build_shield' in order.keys():
            table.loc['Построить щит над', planet.name()] = ','.join([c.name() for c in order['build_shield']])
        if 'attack' in order.keys():
            table.loc['Аттаковать', planet.name()] = ', '.join(map(lambda planet, cities: ', '.join(map(lambda c: f'{c.name()} ({planet.name()})', cities)), order['attack'].keys(), order['attack'].values()))
        if 'eco boost' in order.keys():
            table.loc['Отправить метеорит в аномалию', planet.name()] = 'Да' if order['eco boost'] else 'Нет'
        else:
            table.loc['Отправить метеорит в аномалию', planet.name()] = 'Нет'
        if 'invent' in order.keys():
            table.loc['Изобрести технологию отправки метеоритов', planet.name()] = 'Да'
        else:
            if planet.is_invented():
                table.loc['Изобрести технологию отправки метеоритов', planet.name()] = 'Изобретено'
            else:
                table.loc['Изобрести технологию отправки метеоритов', planet.name()] = 'Нет'
        if 'create_meteorites' in order.keys():
            table.loc['Закупить метеориты', planet.name()] = order['create_meteorites']
    table.to_excel(writers[n], f'{games[n][0].show_round()} раунд')
    games[n][0].end_this_round()
    for pl, msgs in games[n][2].items():
        id = users_online[pl.login()]
        for type, msg in msgs.items():
            if type == 'end_negotiations':
                await bot.delete_message(id, msg.message_id)
                pl.end_negotiations()
            elif type != 'other_planets_info':
                await bot.delete_message(id, msg.message_id)
            else:
                for msg1 in msg.values():
                    await bot.delete_message(id, msg1.message_id)
        if games[n][2][pl].get('end_negotiations'):
            games[n][2][pl].pop('end_negotiations')
    round = games[n][0].show_round()
    for user in games[n][0].active_users():
        await bot.send_message(users_online[user], Messages['end_of_round'].format(round) if round != 6 else Messages['end_of_the_game'], 'MarkdownV2')
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
                                caption=Messages['round_results'].format(round))
    if round == 6:
        writers[n].close()
        writers[n] = None
        if len(writers) == writers.count(None):
            writers = []
        games[n][0].end_this_game()
        for admin in games[n][1]:
            await bot.send_document(admin,
                                    InputFile(f'game results {n + 1}.xlsx'),
                                    caption=Messages['game_results'])
        ac_users = games[n][0].active_users()
        ads = games[n][1]
        for login in ac_users:
            games[n][0].kick_user(login)
            common_users.pop(login)
            available_logins.append(login)
            await bot.send_message(users_online[login], Messages['goodbye'])
            users_online.pop(login)
        for admin in ads:
            games[n][1].remove(admin)
            await bot.send_message(admin, Messages['goodbye'], reply_markup=start_admin_keyboard)
        games[n] = None
        if len(games) == games.count(None):
            games = []    
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
        return Messages['sanctions_info'].format('На вас наложили санкции: ' + ', '.join(sanctions))

def meteorites_message(planet: Planet) -> str:
    if planet.is_invented():
        word = morph.parse('метеорит')[0]
        word = word.make_agree_with_number(planet.meteorites_count()).word
        return f'*Метеориты:*\n_У вас {planet.meteorites_count()} {word}_ ☄️'
    else:
        return '*Метеориты:*\n_У вас не разработана технология отправки метеоритов_'

def eco_message(game: Game) -> str:
    return Messages['eco_info'].format(100 - game.eco_rate)

def other_planets_message(planet: Planet) -> str:
    args = [planet.name()]
    for city in planet.cities():
        args.extend([city.name() + (' ❌' if city.development() == 0 else ''), city.development()])
    return Messages['other_planet'].format(*args)
        

def gameid_by_login(login: str) -> int:
    for i in range(len(games)):
        ans = games[i][0].get_homeland(login)
        if ans is not None:
            return i

async def method_executor(method, id : int, *args):
    try:
        method(*args)
    except NotEnoughMoney:
        await bot.answer_callback_query(id, Messages['not_enough_money'], True)
        return False
    except AlreadyBuiltShield:
        await bot.answer_callback_query(id, Messages['already_built'], True)
        return False
    except NotEnoughRockets:
        await bot.answer_callback_query(id, Messages['not_enough_rockets'], True)
        return False
    except BusyAtTheMoment:
        await bot.answer_callback_query(id, Messages['busy_at_the_moment'], True)
        return False
    except BilateralNegotiations:
        await bot.answer_callback_query(id, Messages['bilateral_negotiations'], True)
        return False
    except NegotiationsOutside:
        await bot.answer_callback_query(id, Messages['negotiations_outside_the_round'], True)
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
        if game.state() == 'passive':
            await bot.send_message(users_online[login], Messages['first_round'], parse_mode='MarkdownV2')
            games[gameid][2][planet]['city_info'] = await bot.send_message(users_online[login], city_stats_message(planet), reply_markup=start_city_keyboard(planet.cities(), planet.order().get('develop', [])), parse_mode='MarkdownV2')
            games[gameid][2][planet]['meteorites_info'] = await bot.send_message(users_online[login], meteorites_message(planet), reply_markup=invent_meteorites_keyboard(planet.order().get('invent', False)), parse_mode='MarkdownV2')
            games[gameid][2][planet]['sanctions_info'] = await bot.send_message(users_online[login], sanctions_message(planet), parse_mode='MarkdownV2')
            games[gameid][2][planet]['eco_info'] = await bot.send_message(users_online[login], eco_message(game), parse_mode='markdownV2')
        elif game.state() == 'active':
            cities = [c for c in planet.cities() if c.development() != 0]
            games[gameid][2][planet]['city_info'] = await bot.send_message(users_online[login], city_stats_message(planet), reply_markup=city_keyboard(cities, planet.order().get('build_shield', []), planet.order().get('develop', [])), parse_mode='MarkdownV2')
            games[gameid][2][planet]['meteorites_info'] = await bot.send_message(users_online[login], meteorites_message(planet), reply_markup=meteorites_keyboard(planet.order().get('create_meteorites', 0)) if planet.is_invented() else invent_meteorites_keyboard(planet.order().get('invent', False)), parse_mode='MarkdownV2')
            planets = list(game.planets().keys())
            planets.remove(planet.name())
            games[gameid][2][planet]['sanctions_info'] = await bot.send_message(users_online[login], sanctions_message(planet), parse_mode='MarkdownV2', reply_markup=sanctions_keyboard(planets, planet.order().get('sanctions', [])))
            games[gameid][2][planet]['eco_info'] = await bot.send_message(users_online[login], eco_message(game), parse_mode='markdownV2', reply_markup=eco_keyboard(planet.order().get('eco boost', False)))
            for pl in game.planets().values():
                if pl.name() != planet.name():
                    games[gameid][2][planet]['other_planets_info'][pl.name()] = await bot.send_message(users_online[login], other_planets_message(pl), 'MarkdownV2', reply_markup=other_planets_keyboard(pl, planet.order().get('attack', dict()).get(pl, [])))
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
        await message.answer(Messages['first_round_for_admins'], 'MarkdownV2', reply_markup=types.ReplyKeyboardRemove())
        games[game_id].append(dict())
        for user in game.all_users():
            planet = game.get_homeland(user)
            await bot.send_message(users_online[user], Messages['first_round'], parse_mode='MarkdownV2')
            games[game_id][2][planet] = dict()
            games[game_id][2][planet]['city_info'] = await bot.send_message(users_online[user], city_stats_message(planet), reply_markup=start_city_keyboard(planet.cities(), []), parse_mode='MarkdownV2')
            games[game_id][2][planet]['meteorites_info'] = await bot.send_message(users_online[user], meteorites_message(planet), reply_markup=invent_meteorites_keyboard(False), parse_mode='MarkdownV2')
            games[game_id][2][planet]['sanctions_info'] = await bot.send_message(users_online[user], sanctions_message(planet), parse_mode='MarkdownV2')
            games[game_id][2][planet]['eco_info'] = await bot.send_message(users_online[user], eco_message(game), parse_mode='markdownV2')
        await timer(game_id, 60)
    
@dp.callback_query_handler(state=BotStates.planets_numbers)
async def set_number_of_planets(call: types.CallbackQuery, state: FSMContext):
    global available_logins
    number = int(call.data)
    game_logins = available_logins[-number:]
    available_logins = available_logins[:-number]
    games.append([Game(number, game_logins), []])
    writers.append(pd.ExcelWriter(f'round results\\game results {len(games)}.xlsx'))
    planets = games[-1][0].info()
    message_text = f'Игра {len(games)} на {number} человек успешно создана\\!\nВот логины для входа:\n'
    for planet in planets.keys():
        if planet != 'eco_rate':
            login = games[-1][0].info(planet)['login']
            common_users[login] = (len(games) - 1, planet)
            message_text += f'{login} \\- _{planet}_\n'
    await call.message.answer(text=message_text, parse_mode='MarkdownV2')
    await state.finish()

@dp.callback_query_handler(state=BotStates.entering_game)
async def choose_lobby(call: types.CallbackQuery, state: FSMContext):
    number = int(call.data)
    games[number - 1][1].append(call.from_user.id)
    await call.message.answer(Messages['entering_game_admin'].format(number), reply_markup=ingame_admin_keyboard)
    await state.finish()


################################################# Внутриигровые команды ###################################################
@dp.callback_query_handler(lambda call: call.data == 'end_negotiations')
async def end_negotiations(call : types.CallbackQuery, state: FSMContext):
    message = call.message
    id = call.from_user.id
    login = None
    for ulog, uid in users_online.items():
        if id == uid:
            login = ulog
            break
    gid = gameid_by_login(login)
    planet = games[gid][0].get_homeland(login)
    await method_executor(planet.end_negotiations, call.id)
    for admin in games[gid][1]:
        await bot.send_message(admin, Messages['negotiations_ended_for_admin'].format(planet.name()))
    await message.answer(Messages['negotiations_ended'])
    games[gid][2][planet].pop('end_negotiations')
    await bot.delete_message(id, message.message_id)
    

@dp.callback_query_handler()
async def ingame_action(call: types.CallbackQuery, state: FSMContext):
    message = call.message
    id = call.from_user.id
    login = None
    for ulog, uid in users_online.items():
        if id == uid:
            login = ulog
            break
    gid = gameid_by_login(login)
    planet = games[gid][0].get_homeland(login)
    type_message = None
    if call.data.startswith(('accept', 'deny')):
        pl = call.data.split()[1]
        ac_planet = games[gid][0].planets()[pl]
        if call.data.startswith('accept'):
            res = await method_executor(planet.accept_diplomatist_from, call.id, ac_planet)
            if res:
                games[gid][2][planet]['end_negotiations'] = await message.answer(Messages['wait_for_diplomatist'].format(ac_planet.name()), reply_markup=end_conversations_keyboard)
                await bot.delete_message(id, message.message_id)
                for admin in games[gid][1]:
                    await bot.send_message(admin, Messages['negotiations_for_admin'].format(planet.name(), ac_planet.name()))
                await bot.send_message(users_online[ac_planet.login()], Messages['negotiations_accepted'].format(planet.name()))
            return
        else:
            await bot.send_message(users_online[ac_planet.login()], Messages['negotiations_denied'].format(planet.name()))
            await bot.delete_message(id, message.message_id)
            return   
    for tp, msg in games[gid][2][planet].items():
        if msg == message:
            type_message = tp
            break
        elif isinstance(msg, dict):
            for pl, msg1 in msg.items():
                if msg1 == message:
                    type_message = f'other_planets_info {pl}'
                    break
    if type_message == 'city_info':
        command, city_name = call.data.split()
        city = None
        for c in planet.cities():
            if c.name() == city_name:
                city = c
                break
        if command == 'develop':
            res = await method_executor(planet.develop_city, call.id, city)
            if not res: return
        else:
            res = await method_executor(planet.build_shield, call.id, city)
            if not res: return
    elif type_message == 'meteorites_info':
        if call.data == 'invent':
            res = await method_executor(planet.invent, call.id)
            if not res: return
            games[gid][2][planet]['meteorites_info'] = await bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=invent_meteorites_keyboard(planet.order()['invent']))
        else:
            n = int(call.data[-1])
            res = await method_executor(planet.create_meteorites, call.id, n)
            if not res: return
            games[gid][2][planet]['meteorites_info'] = await message.edit_text(meteorites_message(planet), 'MarkdownV2', reply_markup=meteorites_keyboard(n))
    elif type_message == 'eco_info':
        res = await method_executor(planet.eco_boost, call.id)
        if res:
            markup = games[gid][2][planet]['meteorites_info'].reply_markup
            games[gid][2][planet]['meteorites_info'] = await games[gid][2][planet]['meteorites_info'].edit_text(meteorites_message(planet), 'MarkdownV2', reply_markup=markup)
            games[gid][2][planet]['eco_info'] = await bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=eco_keyboard(planet.order()['eco boost']))
        return
    elif type_message == 'sanctions_info':
        pl_name = call.data.split()[1]
        planets = list(games[gid][0].planets().keys())
        planets.remove(planet.name())
        await method_executor(planet.send_sanctions, call.id, pl_name)
        games[gid][2][planet]['sanctions_info'] = await bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=sanctions_keyboard(planets, planet.order()['sanctions']))
        return
    elif type_message.startswith('other_planets_info'):
        pl = type_message.split()[1]
        ac_planet = games[gid][0].planets()[pl]
        command, cty = call.data.split()
        if command == 'attack':
            ac_city = list(filter(lambda city: city.name() == cty,ac_planet.cities()))[0]
            res = await method_executor(planet.attack, call.id, ac_city)
            if res:
                markup = games[gid][2][planet]['meteorites_info'].reply_markup
                games[gid][2][planet]['meteorites_info'] = await games[gid][2][planet]['meteorites_info'].edit_text(meteorites_message(planet), 'MarkdownV2', reply_markup=markup)
                games[gid][2][planet]['other_planets_info'][pl] = await bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=other_planets_keyboard(ac_planet, planet.order()['attack'][ac_planet]))
            return
        elif command == 'transaction':
            async with state.proxy() as data:
                data['from_planet'] = planet.name()
                data['to_planet'] = ac_planet.name()
                data['game_id'] = gid
            await message.answer(Messages['how_much_money'].format(ac_planet.name()))
            await BotStates.transaction_state.set()
            return
        else:
            await bot.send_message(users_online[ac_planet.login()], Messages['negotiations_offer'].format(planet.name()), reply_markup=negotiations_offer_keyboard(planet))
            await message.answer(Messages['wait_for_acception'].format(ac_planet.name()))
            return

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

@dp.message_handler(lambda message: message.from_id in admin_ids, commands=['snround'])
async def start_next_round(message: types.Message):
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
        await message.answer(Messages['round_for_admins'].format(num2words(game.show_round(), lang='ru', to='ordinal').capitalize()), 'MarkdownV2', reply_markup=types.ReplyKeyboardRemove())
        for user in game.all_users():
            planet = game.get_homeland(user)
            await bot.send_message(users_online[user], Messages['common_round'].format(num2words(game.show_round(), lang='ru', to='ordinal').capitalize()), parse_mode='MarkdownV2')
            cities = [c for c in planet.cities() if c.development() != 0]
            games[game_id][2][planet]['city_info'] = await bot.send_message(users_online[user], city_stats_message(planet), reply_markup=city_keyboard(cities, [], []), parse_mode='MarkdownV2')
            games[game_id][2][planet]['meteorites_info'] = await bot.send_message(users_online[user], meteorites_message(planet), reply_markup=meteorites_keyboard(0) if planet.is_invented() else invent_meteorites_keyboard(False), parse_mode='MarkdownV2')
            planets = list(game.planets().keys())
            planets.remove(planet.name())
            games[game_id][2][planet]['sanctions_info'] = await bot.send_message(users_online[user], sanctions_message(planet), parse_mode='MarkdownV2', reply_markup=sanctions_keyboard(planets, []))
            games[game_id][2][planet]['eco_info'] = await bot.send_message(users_online[user], eco_message(game), parse_mode='markdownV2', reply_markup=eco_keyboard(False))
            if 'other_planets_info' not in games[game_id][2][planet]: games[game_id][2][planet]['other_planets_info'] = dict()
            for pl in game.planets().values():
                if pl.name() != planet.name():
                    games[game_id][2][planet]['other_planets_info'][pl.name()] = await bot.send_message(users_online[user], other_planets_message(pl), 'MarkdownV2', reply_markup=other_planets_keyboard(pl, []))
        await timer(game_id, 90)

@dp.message_handler(state=BotStates.transaction_state)
async def set_amount_of_money(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount == 0:
            await state.finish()
            return
        async with state.proxy() as data:
            gid = data['game_id']
            from_planet = games[gid][0].planets()[data['from_planet']]
            to_planet = games[gid][0].planets()[data['to_planet']]
            from_planet.transfer(to_planet, amount)
            markup = games[data['game_id']][2][from_planet]['city_info'].reply_markup
            games[data['game_id']][2][from_planet]['city_info'] = await games[data['game_id']][2][from_planet]['city_info'].edit_text(city_stats_message(from_planet), reply_markup=markup, parse_mode='MarkdownV2')
            markup = games[data['game_id']][2][to_planet]['city_info'].reply_markup
            games[data['game_id']][2][to_planet]['city_info'] = await games[data['game_id']][2][to_planet]['city_info'].edit_text(city_stats_message(to_planet), reply_markup=markup, parse_mode='MarkdownV2')
            await message.answer(Messages['successful_transaction'].format(to_planet.name()))
            await bot.send_message(users_online[to_planet.login()], Messages['transaction_notification'].format(from_planet.name(), amount))
        await state.finish()
    except NotEnoughMoney:
        await message.answer(Messages['not_enough_for_transaction'])
        return
    except ValueError:
        await message.answer(Messages['wrong_answer'])
        return 

@dp.message_handler(lambda message: message.from_id in admin_ids, commands=['endgame'])
async def end_the_game(message: types.Message):
    global games, users_online, writers
    gid = None
    for i in range(len(games)):
        if message.from_id in games[i][1]:
            gid = i
            break
    if gid is None:
        await message.answer(Messages['ending_outside'])
        return
    elif games[gid][0].state() == 'inactive':
        await message.answer(Messages['ending_when_not_started'])
        return
    else:
        if len(writers[gid].sheets) == 0:
            pd.DataFrame([[]]).to_excel(writers[gid], '1')
        writers[gid].close()
        writers[gid] = None
        if len(writers) == writers.count(None):
            writers = []
        games[gid][0].end_this_game()
        ac_users = games[gid][0].active_users() 
        for login in ac_users:
            games[gid][0].kick_user(login)
            common_users.pop(login)
            available_logins.append(login)
            await bot.send_message(users_online[login], Messages['game_interrupted_message'])
            users_online.pop(login)
        for ad in games[gid][1]:
            await bot.send_message(ad, Messages['game_interrupted_report'], reply_markup=start_admin_keyboard)
        games[gid] = None
        if len(games) == games.count(None):
            games = []

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)