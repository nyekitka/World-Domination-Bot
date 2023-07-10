import telebot
from telebot import types

bot = telebot.TeleBot('6300949258:AAH58zEGG1WSAwjrRdUEVVM21LgsVlVmcKg')
common_users = set()    #обычные пользователи
users_online = dict()   #пользователи онлайн
admins = None           #список админов
admin_ids = set()       #айдишники админов
with open('admins.txt', 'r') as file:
    admins = [line.strip() for line in file]

def login(message):
    if message.text not in admins and message.text not in common_users:
        bot.send_message(message.chat.id, 'Такого пользователя не существует, попробуйте заново')
        bot.register_next_step_handler(message, login)
    elif message.text in users_online.keys():
        bot.send_message(message.chat.id, 'Такой пользователь уже в сети. Введите другого пользователя')
        bot.register_next_step_handler(message, login)
    elif message.text in admins:
        users_online[message.txt] = message.from_user.id
        admin_ids.add(message.from_user.id)
        markup = types.ReplyKeyboardMarkup()
        button1 = types.KeyboardButton('Создать игру')
        button2 = types.KeyboardButton('Войти в игру')
        markup.row(button1)
        markup.row(button2)
        bot.send_message(message.chat.id, f'Добро пожаловать, {message.text}!', reply_markup=markup)
        bot.register_next_step_handler(message, game_management)
    else:
        users_online[message.txt] = message.from_user.id
        bot.send_message(message.chat.id, f'Добро пожаловать, {message.text}!')
    
@bot.message_handler(commands=['start'])
def initializer(message):
    bot.send_message(message.chat.id, 'Введите свой логин')
    bot.register_next_step_handler(message, login)
    
@bot.message_handler(commands=['create_game'])
def game_management(message):
    if message.text.lower() in ['создать игру', '/create_game']:
        if message.from_user.id not in admin_ids:
            bot.send_message(message.chat.id, 'Вы не можете создать игру, т.к. не являетесь администратором')
        else:
            bot.send_message(message.chat.id, 'Введите название лобби')
    bot.send_message(message.chat.id, 'Введите название лобби')

bot.polling(non_stop=True)