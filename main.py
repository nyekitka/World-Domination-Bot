from random import shuffle
from zipfile import ZipFile
import asyncio
import os
import logging
import json

import psycopg2
import numpy as np
import pandas as pd
from dotenv import dotenv_values
from aiogram import Dispatcher, Bot, types, F
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, CommandStart, CommandObject

import keyboards as kb
from game_classes import City, Planet, Game, CDException, User
from messages import Messager
from page import html_page_generator, css_generator

class BotStates(StatesGroup):
    """
    All possible state of the bot:
    - planets_numbers - admin is choosing a number of planets in the game;
    - choose_pack - admin chooses a pack of planets and cities;
    - transaction_state - state for the transaction process
    """

    planets_numbers = State()
    choose_pack = State()
    choose_lobby_admin = State()
    choose_lobby = State()
    transaction_state = State()

env_config = dotenv_values()
bot_token = env_config['BOT_TOKEN']
round_length = int(env_config['ROUND_LENGTH'])

logging.basicConfig(level=logging.INFO)

# database initialization

db_connection = psycopg2.connect(
    dbname=env_config['DATABASE_NAME'],
    user=env_config['USER_NAME'],
    password=env_config['DATABASE_PASSWORD'],
    host=env_config['DATABASE_HOST'],
    port=env_config['PORT']
)
cursor = db_connection.cursor()
    
storage = MemoryStorage()
bot = Bot(token=bot_token)
dp = Dispatcher(storage=storage)
messager = Messager(db_connection)
OwnerID = env_config['OWNER']

############################################ Вспомогательные функции ##################################################
        
async def timer(game: Game, secs: int = round_length):
    await asyncio.sleep(secs // 2)
    if not game.exists():
        return
    for user in game.active_users():
        await bot.send_message(user.id, messager.fivemin())
    for admin in game.admins_list():
        await bot.send_message(admin.id, messager.fivemin())
    await asyncio.sleep(secs // 2 - secs // 10)
    if not game.exists():
        return
    for user in game.active_users():
        await bot.send_message(user.id, messager.onemin())
    for admin in game.admins_list():
        await bot.send_message(admin.id, messager.onemin())
    await asyncio.sleep(secs // 10)
    if not game.exists():
        return
    
    messages = game.get_all_messages()
    for msgid, userid in messages:
        try:
            await bot.delete_message(userid, msgid)
        except:
            print(msgid, userid)
    game.delete_all_messages()
    game.end_this_round()
    round = game.show_round()
    for user in game.active_users():
        await bot.send_message(user.id, messager.round_end(round), parse_mode='MarkdownV2')
    if round == 1:
        css_generator(game)
    html_page_generator(game)
    os.chdir("round results")
    with ZipFile(f'{game.id} game {round} round results.zip', 'w') as zfile:
        zfile.write(f'style{game.id}.css')
        zfile.write(f'results_{game.id}_{round}.html')
        for file in os.listdir('fonts'):
            zfile.write(f'fonts\\{file}')
    for admin in game.admins_list():
        await bot.send_document(admin.id, 
                                FSInputFile(f'{game.id} game {round} round results.zip'),
                                caption=messager.admin_round_end(round))
    if round == 6:
        game.extract_orders_data(f'.\\excel files\\game {game.id} results.xlsx')
        for admin in game.admins_list():
            await bot.send_document(admin.id,
                                    FSInputFile(f'game results {game.id}.xlsx'),
                                    caption=messager.game_results())
            await bot.send_message(admin.id, messager.goodbye())
        for user in game.active_users():
            await bot.send_message(admin.id, messager.end_of_the_game(), parse_mode='MarkdownV2')
            await bot.send_message(admin.id, messager.goodbye())
        game.end_game()
    os.chdir('..')
        
async def method_executor_call(method, call : types.CallbackQuery, *args):
    try:
        method(*args)
    except CDException as ex:
        await call.answer(str(ex), True)
        return False
    return True

async def method_executor_msg(method, userid : int, *args, reply_markup=None):
    try:
        method(*args)
    except CDException as ex:
        await bot.send_message(userid, str(ex), reply_markup=reply_markup)
        return False
    return True
        
async def print_all_info(nround: int, planet: Planet, userid: int):
    await bot.send_message(userid, messager.round_message(nround), 
                           parse_mode='MarkdownV2')
    city_msg = await bot.send_message(userid, messager.city_stats_message(planet), 
                                        reply_markup=kb.city_keyboard(nround, planet, planet.cities(), 
                                                                        planet.ordered_shield_cities(), planet.developed_cities()),
                                        parse_mode='MarkdownV2')
    ikm = kb.invent_meteorites_keyboard(planet, planet.is_invent_in_order()) if not planet.is_invented() else kb.meteorites_keyboard(planet, planet.number_of_ordered_meteorites())
    meteorites_msg = await bot.send_message(userid, messager.meteorites_message(planet),
                                                reply_markup=ikm,
                                                parse_mode='MarkdownV2')
    sanctions_msg = await bot.send_message(userid, messager.sanctions_message(planet),
                                                reply_markup=kb.sanctions_keyboard(planet, planet.game().planets(), 
                                                                                    planet.ordered_sanctions_list()),
                                                parse_mode='MarkdownV2')
    eco_msg = await bot.send_message(userid, messager.eco_message(planet.game()),
                                            reply_markup=kb.eco_keyboard(planet, planet.is_planned_eco_boost()),
                                            parse_mode='MarkdownV2')
    cursor.execute("""INSERT INTO InfoMessages(ID, MType, PlanetID) VALUES
                    (%s, 'City', %s),
                    (%s, 'Meteorites', %s),
                    (%s, 'Sanctions', %s),
                    (%s, 'Eco', %s)""", 
                    (city_msg.message_id, planet.id, 
                    meteorites_msg.message_id, planet.id, 
                    sanctions_msg.message_id, planet.id, 
                    eco_msg.message_id, planet.id))
    for other_planet in planet.game().planets():
        if planet != other_planet:
            msg = await bot.send_message(userid, messager.other_planets_message(other_planet),
                                            reply_markup=kb.other_planets_keyboard(nround, planet, other_planet, 
                                                                                planet.ordered_attack_cities(other_planet)),
                                        parse_mode='MarkdownV2')
            cursor.execute("INSERT INTO PlanetMessages(OwnerID, PlanetID, MessageID, MType) VALUES (%s, %s, %s, 'Attack')", 
                            (planet.id, other_planet.id, msg.message_id))
    db_connection.commit()

############################################### Команды вне игры #######################################################


@dp.message(CommandStart())
async def start(message : types.Message):
    tgid = message.from_user.id
    user = User.init_with_check(tgid, db_connection)
    if user is None:
        User.make_new_user(tgid, False, db_connection)
        await message.answer(messager.start_msg(False, False, message.from_user.first_name),
                             reply_markup=kb.start_keyboard(False))
    else:
        isadmin = user.is_admin()
        await message.answer(messager.start_msg(isadmin, user.game() is not None, message.from_user.first_name),
                             reply_markup=kb.start_keyboard(isadmin))

@dp.message(Command('knight'), F.from_user.id == OwnerID)
async def knight(message: types.Message, command: CommandObject):
    username = command.args.strip()
    if username.startswith('@'):
        user = await bot.get_chat(username)
        cursor.execute("DELETE FROM \"User\" WHERE tgid=%s", (user.id,))
        cursor.execute("INSERT INTO Admins(tgid) VALUES (%s)", (user.id,))
        await bot.send_message(user.id, messager.knight())
        await message.answer(messager.knighting_for_leader(user.first_name))

@dp.message(Command('unknight'), F.from_user.id == OwnerID)
async def unknight(message: types.Message, command: CommandObject):
    username = command.args.strip()
    if username.startswith('@'):
        user = await bot.get_chat(username)
        cursor.execute("DELETE FROM Admins WHERE tgid=%s", (user.id,))
        cursor.execute("INSERT INTO \"User\"(tgid) VALUES (%s)", (user.id,))
        await bot.send_message(user.id, messager.unknight())
        await message.answer(messager.unknighting_for_leader(user.first_name))


@dp.message((F.text == 'Войти в игру') & F.chat.func(lambda user: not User(user.id, db_connection).is_admin()))
async def enter_game(message: types.Message, state: FSMContext):
    all_games = Game.all_games(db_connection)
    if len(all_games) == 0:
        await message.answer(messager.no_games(), reply_markup=kb.start_keyboard(False))
    else:
        await state.set_state(BotStates.choose_lobby)
        await message.answer(messager.choose_lobby(), reply_markup=kb.choose_lobby_keyboard(all_games))

@dp.message((F.text == 'Войти в игру') & F.chat.func(lambda user: User(user.id, db_connection).is_admin()))       
async def admin_game(message: types.Message, state: FSMContext):
    all_games = Game.all_games(db_connection)
    if len(all_games) == 0:
        await message.answer(messager.no_games(), reply_markup=kb.start_keyboard(True))
    else:
        await state.set_state(BotStates.choose_lobby_admin)
        await message.answer(messager.choose_lobby(), reply_markup=kb.choose_lobby_keyboard(all_games))

@dp.message(F.text == 'Выйти из игры')
async def leave_lobby(message: types.Message):
    tgid = message.from_user.id
    user = User(tgid, db_connection)
    game = user.game()
    planet = None
    if game is not None:
        planet = game.get_homeland(user.id)
    res = await method_executor_msg(user.kick_user, tgid, reply_markup=kb.start_keyboard(user.is_admin()))
    if res:
        if not user.is_admin():
            await message.answer(messager.leaving_msg(),
                           reply_markup=kb.start_keyboard(user.is_admin()))
            mids = game.get_all_user_messages(user)
            await bot.delete_messages(user.id, mids)
            status = game.status()
            game.delete_all_user_messages(user)
            if status == 'Waiting':
                active_users = game.active_users()
                num_users = game.number_of_planets()
                for ouser in active_users:
                    await bot.send_message(ouser.id, messager.leave_for_others(planet.name(), len(active_users), num_users))
        else:
            await message.answer(messager.leaving_msg(), 
                                 reply_markup=kb.start_keyboard(user.is_admin()))

@dp.message(Command('help'))
async def help(message : types.Message):
    with open('help.txt', 'r', encoding='UTF-8') as file:
        text = ''.join(file.readlines())
        await message.answer(text=text, parse_mode='MarkdownV2')

############################################# Кнопочные команды вне игры #################################################

@dp.message((F.text == 'Создать игру') & F.chat.func(lambda user: User(user.id, db_connection).is_admin()))
async def create_game(message : types.Message, state: FSMContext):
    await message.answer("Выберите набор планет и городов для игры", reply_markup=kb.pack_keyboard())
    await state.set_state(BotStates.choose_pack)

@dp.message((F.text == 'Начать игру') & F.chat.func(lambda user: User(user.id, db_connection).is_admin()))
async def start_game(message : types.Message):
    admin = User(message.from_user.id, db_connection)
    game = admin.game()
    if game is None:
        await message.answer(messager.starting_game_not_being_in(), reply_markup=kb.start_keyboard(True))
    elif game.status() == 'Waiting' and game.is_all_active():
        all_admins = game.admins_list()
        all_planets = game.planets()
        game.start_new_round()
        for admin in all_admins:
            await bot.send_message(admin.id, messager.round_admins(1), parse_mode='MarkdownV2')
        for planet in all_planets:
            user_id = planet.user_id()
            await print_all_info(1, planet, user_id)
        await timer(game)
    elif game.status() != 'Waiting':
        await message.answer(messager.already_started())
    else:
        await message.answer(messager.not_enough_players(len(game.active_users()), game.number_of_planets()))

@dp.callback_query(BotStates.choose_pack)
async def set_pack(call: types.CallbackQuery, state: FSMContext):
    pack = call.data
    await call.answer('')
    await call.message.answer('Выберите количество планет в игре', reply_markup=kb.number_of_planets_keyboard(pack))
    await state.set_state(BotStates.planets_numbers)

@dp.callback_query(BotStates.choose_lobby_admin)
async def chosen_lobby_admin(call: types.CallbackQuery, state: FSMContext):
    await call.answer('')
    gamecode = int(call.data)
    tgid = call.from_user.id
    game = Game.init_with_check(gamecode, db_connection)
    res = await method_executor_msg(game.join_admin, tgid, tgid)
    if res:
        await call.message.answer(messager.success_admin_enter(gamecode),
                                reply_markup=kb.ingame_keyboard(True))
    await state.clear()

@dp.callback_query(BotStates.choose_lobby)
async def chosen_lobby(call: types.CallbackQuery, state: FSMContext):
    await call.answer('')
    gamecode = int(call.data)
    tgid = call.from_user.id
    game = Game.init_with_check(gamecode, db_connection)
    res = await method_executor_msg(game.join_user, tgid, tgid)
    if res:
        planet = game.get_homeland(tgid)
        await call.message.answer(messager.success_enter(gamecode, planet.name()), reply_markup=kb.ingame_keyboard(False))
        status = game.status()
        if status == 'Waiting':
            active_users = game.active_users()
            num_users = game.number_of_planets()
            for ouser in active_users:
                await bot.send_message(ouser.id, messager.success_enter_for_others(planet.name(), len(active_users), num_users))
            for admin in game.admins_list():
                await bot.send_message(admin.id, messager.success_enter_for_others(planet.name(), len(active_users), num_users))
        elif status == 'Negotiations':
            await print_all_info(game.show_round(), planet, tgid)
    await state.clear()

@dp.callback_query(BotStates.planets_numbers)
async def set_number_of_planets(call: types.CallbackQuery, state: FSMContext):
    number, pack = call.data.split(',')
    number = int(number)
    file = open('presets\\planets_and_cities.json', encoding='utf-8')
    plncities = json.load(file)
    pack = plncities[pack]
    game = Game.make_new_game(number, db_connection)
    for i, key in enumerate(pack.keys()):
        if i == number:
            break
        planet = Planet.make_new_planet(key, game.id, db_connection)
        for city in pack[key]:
            City.make_new_city(city, planet.id, db_connection)
    await call.answer('')
    await call.message.answer(text=messager.game_created(game.id, number), 
                              reply_markup=kb.start_keyboard(True))
    await state.clear()


################################################# Внутриигровые команды ###################################################
@dp.callback_query(F.data == 'end_negotiations')
async def end_negotiations(call : types.CallbackQuery, state: FSMContext):
    message = call.message
    id = call.from_user.id
    user = User(id, db_connection)
    game = user.game()
    planet = game.get_homeland(user.id)
    res = await method_executor_call(planet.end_negotiations, call.id)
    if res:
        for admin in game.admins_list():
            await bot.send_message(admin.id, messager.negotiations_ended_admin(planet.name()))
    await message.answer(messager.negotiations_ended())
    await bot.delete_message(id, message.message_id)
    

@dp.callback_query(lambda c: c.data.split()[0] in [
    'accept', 'deny', 'develop',
    'defend', 'sanctions', 'invent',
    'create', 'eco', 'attack',
    'negotiations', 'transaction'
])
async def ingame_action(call: types.CallbackQuery, state: FSMContext):
    message = call.message
    id = call.from_user.id
    user = User(id, db_connection)
    game = user.game()
    args = call.data.split()
    planet = Planet(int(args[1]), db_connection)
    round = game.show_round()
    old_balance = planet.balance()
    old_num_meteorites = planet.meteorites()
    if args[0] == 'accept' or args[0] == 'deny':
        from_planet = Planet(int(args[2]), db_connection)
        # Acception of negotiations
        if args[0] == 'accept':
            res = await method_executor_call(planet.accept_diplomatist_from, call, from_planet)
            if res:
                call.answer('')
                msg = await message.answer(messager.wait_for_diplomatist(from_planet.name()), reply_markup=kb.end_negotiations_keyboard)
                cursor.execute("UPDATE PlanetMessages SET messageid=%s WHERE messageid=%s AND mtype='Negotiations'",
                               (msg.message_id, message.message_id))
                db_connection.commit()
                await bot.delete_message(id, message.message_id)
                for admin in game.admins_list():
                    await bot.send_message(admin.id, messager.neg_accept_for_admin(planet.name(), from_planet.name()))
                await bot.send_message(from_planet.user_id(), messager.negotiations_accepted(planet.name()))

        # Denying of negotiations
        else:
            call.answer('')
            await bot.send_message(from_planet.user_id(), messager.negotiations_denied(planet.name()))
            cursor.execute("DELETE FROM PlanetMessages WHERE messageid=%s AND mtype='Negotiations'", (message.message_id,))
            db_connection.commit()
            await bot.delete_message(id, message.message_id)
    
    elif args[0] == 'develop':
        res = await method_executor_call(planet.develop_city, call, int(args[2]))
        if res:
            call.answer('')
            await message.edit_reply_markup(reply_markup=kb.city_keyboard(round, planet, 
                                                                                planet.cities(), planet.ordered_shield_cities(),
                                                                                planet.developed_cities()))
    
    elif args[0] == 'defend':
        res = await method_executor_call(planet.build_shield, call, int(args[2]))
        if res:
            call.answer('')
            await message.edit_reply_markup(reply_markup=kb.city_keyboard(round, planet, planet.cities(),
                                                                                planet.ordered_shield_cities(), planet.developed_cities()))

    elif args[0] == 'sanctions':
        res = await method_executor_call(planet.send_sanctions, call, int(args[2]))
        if res:
            call.answer('')
            await message.edit_reply_markup(reply_markup=kb.sanctions_keyboard(planet, game.planets(), planet.ordered_sanctions_list()))

    elif args[0] == 'invent':
        res = await method_executor_call(planet.invent, call)
        if res:
            call.answer('')
            await message.edit_reply_markup(reply_markup=kb.invent_meteorites_keyboard(planet, planet.is_invent_in_order()))
    
    elif args[0] == 'create':
        res = await method_executor_call(planet.create_meteorites, call, int(args[2]))
        if res:
            call.answer('')
            await message.edit_reply_markup(reply_markup=kb.meteorites_keyboard(planet, planet.number_of_ordered_meteorites()))
    
    elif args[0] == 'eco':
        res = await method_executor_call(planet.eco_boost, call)
        if res:
            call.answer('')
            await message.edit_reply_markup(reply_markup=kb.eco_keyboard(planet, planet.is_planned_eco_boost()))
    
    elif args[0] == 'attack':
        res = await method_executor_call(planet.attack, call, int(args[2]))
        if res:
            call.answer('')
            other_planet = City(int(args[2]), db_connection).planet()
            await message.edit_reply_markup(reply_markup=kb.other_planets_keyboard(round, planet, other_planet, 
                                                                            planet.ordered_attack_cities(other_planet)))
    
    elif args[0] == 'negotiations':
        call.answer('')
        other_planet = Planet(int(args[2]), db_connection)
        other_user_id = other_planet.user_id()
        if other_user_id is None:
            await bot.send_message(id, messager.nobody_online(other_planet.name()))
        else:
            await bot.send_message(id, messager.wait_for_acception(other_planet.name()))
            msg = await bot.send_message(other_user_id, messager.negotiations_offer(planet.name()),
                                         reply_markup=kb.negotiations_offer_keyboard(other_planet, planet))
            cursor.execute("INSERT INTO PlanetMessages(ownerid, planetid, messageid, mtype) VALUES (%s, %s, %s, 'Negotiations')",
                           (other_planet.id, planet.id, msg.message_id))
            db_connection.commit()
    
    else:
        call.answer('')
        other_planet = Planet(int(args[2]), db_connection)
        await state.set_state(BotStates.transaction_state)
        await state.update_data({
            'from_planet' : planet,
            'to_planet' : other_planet,
            'game_id' : game.id
        })
        await message.answer(messager.how_much_money(other_planet.name()))
        await asyncio.sleep(30)
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
            if game.status() == 'Negotiations':
                await message.answer(messager.waiting_time_expired())
    
    new_balance = planet.balance()
    new_num_meteorites = planet.meteorites()
    if old_balance != new_balance:
        cursor.execute("SELECT id FROM InfoMessages WHERE planetid=%s AND mtype='City'", (planet.id,))
        msgid = cursor.fetchone()[0]
        await bot.edit_message_text(messager.city_stats_message(planet), chat_id=id, 
                                          message_id=msgid,reply_markup=kb.city_keyboard(round, planet, 
                                                                                planet.cities(), planet.ordered_shield_cities(),
                                                                                planet.developed_cities()),
                                        parse_mode='MarkdownV2')
    if old_num_meteorites != new_num_meteorites:
        cursor.execute("SELECT id FROM InfoMessages WHERE planetid=%s AND mtype='Meteorites'", (planet.id,))
        msgid = cursor.fetchone()[0]
        chosen_meteorites = planet.number_of_ordered_meteorites()
        msg = await bot.edit_message_text(messager.meteorites_message(planet), chat_id=id, message_id=msgid,
                                          reply_markup=kb.meteorites_keyboard(planet, chosen_meteorites),
                                          parse_mode='MarkdownV2')


@dp.message(Command('snround'), F.chat.func(lambda user: User(user.id, db_connection).is_admin()))
async def start_next_round(message: types.Message):
    user = User(message.from_user.id, db_connection)
    game = user.game()
    if game is None:
        await message.answer(messager.starting_game_not_being_in(), reply_markup=kb.start_keyboard(True))
        return
    res = await method_executor_msg(game.start_new_round, message.message_id)
    if res:
        nround = game.show_round()
        for admin in game.admins_list():
            await bot.send_message(admin.id, messager.round_admins(nround), 
                                   parse_mode='MarkdownV2', reply_markup=types.ReplyKeyboardRemove())
        for user in game.active_users():
            planet = game.get_homeland(user.id)
            await print_all_info(nround, planet, user.id)
        await timer(game)

@dp.message(BotStates.transaction_state)
async def set_amount_of_money(message: types.Message, state: FSMContext):
    amount = None
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(messager.wrong_answer())
        return
    if amount == 0:
        await state.clear()
        return
    data = await state.get_data()
    game_id = data['game_id']
    game = Game(game_id, db_connection)
    from_planet : Planet = data['from_planet']
    to_planet : Planet = data['to_planet']
    res = await method_executor_msg(from_planet.transfer, message.from_user.id, to_planet.id, amount)
    if res:
        nround = game.show_round()
        cursor.execute("SELECT id FROM InfoMessages WHERE planetid=%s AND mtype='City'", (from_planet.id, ))
        from_city_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM InfoMessages WHERE planetid=%s AND mtype='City'", (to_planet.id, ))
        to_city_id = cursor.fetchone()[0]
        from_msg = await bot.edit_message_text(messager.city_stats_message(from_planet), chat_id=from_planet.user_id(), 
                                                message_id=from_city_id, reply_markup=kb.city_keyboard(nround, from_planet, 
                                                                                                        from_planet.cities(), 
                                                                                                        from_planet.ordered_shield_cities(),
                                                                                                        from_planet.developed_cities()),
                                                                                                        parse_mode='MarkdownV2')
        to_msg = await bot.edit_message_text(messager.city_stats_message(to_planet), chat_id=to_planet.user_id(), 
                                                message_id=to_city_id, reply_markup=kb.city_keyboard(nround, to_planet, 
                                                                                                        to_planet.cities(), 
                                                                                                        to_planet.ordered_shield_cities(),
                                                                                                        to_planet.developed_cities()),
                                                                                                        parse_mode='MarkdownV2')
        cursor.execute("UPDATE InfoMessages SET id=%s WHERE id=%s", (from_msg.message_id, from_city_id))
        cursor.execute("UPDATE InfoMessages SET id=%s WHERE id=%s", (to_msg.message_id, to_city_id))
        db_connection.commit()
        await message.answer(messager.successful_transaction(to_planet.name()))
        await bot.send_message(to_planet.user_id(), messager.transaction_notification(to_planet.name(), amount))
        await state.clear()

@dp.message(Command('endgame'), F.chat.func(lambda user: User(user.id, db_connection).is_admin()))
async def end_the_game(message: types.Message):
    user = User(message.from_user.id, db_connection)
    game = user.game()
    if game is None:
        message.answer(messager.ending_outside())
    else:
        for admin in game.admins_list():
            await bot.send_message(admin.id, messager.game_interrupted_report())
        for user in game.active_users():
            await bot.send_message(user.id, messager.game_interrupted_message())
        game.end_game()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)
    


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Working was interrupted.')
        db_connection.close()
    