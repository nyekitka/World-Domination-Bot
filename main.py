import telebot


bot = telebot.TeleBot('6300949258:AAH58zEGG1WSAwjrRdUEVVM21LgsVlVmcKg')
common_users = set()
users_online = set()
admins = None
with open('admins.txt', 'r') as file:
    admins = [line.strip() for line in file]

def login(message):
    if message.text not in admins and message.text not in common_users:
        bot.send_message(message.chat.id, 'Такого пользователя не существует, попробуйте заново')
        bot.register_next_step_handler(message, login)
    elif message.text in users_online:
        bot.send_message(message.chat.id, 'Такой пользователь уже в сети. Введите другого пользователя')
        bot.register_next_step_handler(message, login)
    elif message.text in admins:
        users_online.add(message.text)
        bot.send_message(message.chat.id, f'Добро пожаловать, {message.text}!')
    else:
        users_online.add(message.text)
        bot.send_message(message.chat.id, f'Добро пожаловать, {message.text}!')
    
@bot.message_handler(commands=['start'])
def initializer(message):
    bot.send_message(message.chat.id, 'Введите свой логин')
    bot.register_next_step_handler(message, login)

bot.polling(non_stop=True)