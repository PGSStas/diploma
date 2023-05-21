from telebot import types

from .message_handler import MessageHandler

message_handler = MessageHandler()


@message_handler.bot.message_handler(commands=['start'])
def welcome_message(message: types.Message):
    print("Start by", message.from_user.full_name)
    message_handler.welcome_message(message)
    print("Done Start by", message.from_user.full_name)


@message_handler.bot.message_handler(commands=['help'])
def help_message(message: types.Message):
    print("Help by", message.from_user.full_name)
    message_handler.help_message(message)
    print("Done Help by", message.from_user.full_name)


@message_handler.bot.message_handler(commands=['list'])
def get_list(message: types.Message):
    print("List by", message.from_user.full_name)
    message_handler.print_list(message)
    print("Done List by", message.from_user.full_name)


@message_handler.bot.message_handler(commands=['detail'])
def get_detail(message: types.Message):
    print("Detail by", message.from_user.full_name)
    message_handler.print_cluster(message)
    print("Done Detail by", message.from_user.full_name)


@message_handler.bot.message_handler()
def find_movie(message: types.Message):
    print("Rnd msg by", message.from_user.full_name)
    message_handler.bot.send_message(message.chat.id, "Я не понимаю :(", reply_to_message_id=message.id)
    print("Done Rnd msg by", message.from_user.full_name)


# -- Callbacks --

@message_handler.bot.callback_query_handler(func=lambda call: call.data.startswith('article_id'))
def article_button_press(call: types.CallbackQuery):
    print("Callback news by", call.from_user.full_name)
    message_handler.process_article_button(call)
    print("Done callback news by", call.from_user.full_name)


@message_handler.bot.callback_query_handler(func=lambda call: call.data.startswith('page_id'))
def list_button_press(call: types.CallbackQuery):
    print("Callback list by", call.from_user.full_name)
    message_handler.process_list_button(call)
    print("Done callback list by", call.from_user.full_name)


@message_handler.bot.callback_query_handler(func=lambda call: call.data.startswith('cluster_id'))
def cluster_button_press(call: types.CallbackQuery):
    print("Callback cluster by", call.from_user.full_name)
    message_handler.process_cluster_button(call)
    print("Done callback cluster by", call.from_user.full_name)


@message_handler.bot.callback_query_handler(func=lambda call: call.data == 'clear')
def clear(call: types.CallbackQuery):
    print("Callback clear by", call.from_user.full_name)
    call.message.delete()
    print("Done callback clear by", call.from_user.full_name)
