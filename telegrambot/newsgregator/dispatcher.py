
from aiogram import types
from .message_handler import MessageHandler

message_handler = MessageHandler()


@message_handler.dispatcher.message_handler(commands=['start'])
async def welcome_message(message: types.Message):
    print("Start by", message.from_user.full_name)
    await message_handler.welcome_message(message)


@message_handler.dispatcher.message_handler(commands=['help'])
async def help_message(message: types.Message):
    print("Help by", message.from_user.full_name)
    await message_handler.help_message(message)


@message_handler.dispatcher.message_handler(commands=['list'])
async def get_list(message: types.Message):
    print("List by", message.from_user.full_name)
    # await message.delete()
    await message_handler.print_list(message)


@message_handler.dispatcher.message_handler(commands=['detail'])
async def get_detail(message: types.Message):
    print("Detail by", message.from_user.full_name)
    await message_handler.print_cluster(message)


@message_handler.dispatcher.message_handler()
async def find_movie(message: types.Message):
    print("Rnd msg by", message.from_user.full_name)
    await message.answer("Я не понимаю :(")


# -- Callbacks --

@message_handler.dispatcher.callback_query_handler(message_handler.cd_article.filter())
async def article_button_press(call: types.CallbackQuery, callback_data: dict):
    print("Callback news by", call.from_user.full_name)
    await message_handler.process_article_button(call, callback_data)


@message_handler.dispatcher.callback_query_handler(message_handler.cd_list.filter())
async def article_button_press(call: types.CallbackQuery, callback_data: dict):
    print("Callback list by", call.from_user.full_name)
    await message_handler.process_list_button(call, callback_data)


@message_handler.dispatcher.callback_query_handler(message_handler.cd_cluster.filter())
async def article_button_press(call: types.CallbackQuery, callback_data: dict):
    print("Callback cluster by", call.from_user.full_name)
    await message_handler.process_cluster_button(call, callback_data)


@message_handler.dispatcher.callback_query_handler(message_handler.old_cd_list.filter())
async def article_button_press(call: types.CallbackQuery, callback_data: dict):
    print("Callback old list by", call.from_user.full_name)
    await message_handler.process_list_button(call, callback_data)

@message_handler.dispatcher.callback_query_handler(text="clear")
async def clear(call: types.CallbackQuery):
    print("Callback clear by", call.from_user.full_name)
    await call.message.delete()
