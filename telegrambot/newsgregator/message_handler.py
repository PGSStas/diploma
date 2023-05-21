import sys
sys.path.append('/root/diploma')

from .database import Database, Article
import datetime
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import Dispatcher
from aiogram import Bot, types
import os
import typing as tp


SPLIT_STRING = "\n>================================<\n"


class MessageHandler:
    def __init__(self):
        self.database = Database(os.environ['PG_PASSWORD'])

        self.bot = Bot(token=os.environ['BOT_TOKEN'])
        self.dispatcher = Dispatcher(self.bot)
        # self.dispatcher.setup_middleware(LoggingMiddleware())

        self.old_cd_list = CallbackData("cd_list", "page_id")
        self.cd_list = CallbackData("cd_list", "page_id", "version")
        self.cd_cluster = CallbackData("cd_cluster", "cluster_id")
        self.cd_article = CallbackData("cd_article", "article_id")

        self.list_of_clusters = self.database.get_cluster_titles()
        self.cluster_version = int(datetime.datetime.now().timestamp())
        print(self.list_of_clusters)
        print(len(self.list_of_clusters))

    async def welcome_message(self, message: types.Message) -> None:
        await message.reply("Привет!\nЯ Newsgregator, бот, который собирает для тебя новости мира IT, автопрома, игровой индустрии и кинематографа!\n"
                            "Чтобы узнать как использовать меня почитай /help 😄")

    async def help_message(self, message: types.Message) -> None:
        await message.reply("/help - помощь\n"
                            "/list - обновляет треды новостей за 24 часа, в которых 2 и более артикля. Остальные я считаю нерелевантными :(\n"
                            "/detail [id] - расписать подробнее кластер новостей с определенным ID\n")

    async def create_list_page(self, id: int) -> tp.Tuple[str, types.InlineKeyboardMarkup]:
        first_index = id * 8
        last_index = min(len(self.list_of_clusters), (id + 1)*8)

        keyboard = types.InlineKeyboardMarkup()

        if id != 0:
            keyboard.add(types.InlineKeyboardButton(
                text=f"<<", callback_data=self.cd_list.new(page_id=id - 1, version=self.cluster_version)))

        info_slice = []
        for i, cluster in enumerate(self.list_of_clusters[first_index:last_index]):
            entry = f"#{first_index + i + 1}. {cluster[3]} `/detail {cluster[0]}`"
            # entry = f"#{first_index + i + 1}. {cluster[3]}"
            info_slice.append(entry)
            keyboard.add(types.InlineKeyboardButton(
                text=f"Группа {first_index + i + 1}", callback_data=self.cd_cluster.new(cluster_id=cluster[0])))

        answer = SPLIT_STRING.join(info_slice)

        if len(self.list_of_clusters) // 8 > id:
            keyboard.add(types.InlineKeyboardButton(
                text=f">>", callback_data=self.cd_list.new(page_id=id + 1, version=self.cluster_version)))

        keyboard.add(types.InlineKeyboardButton(
            text="Clear", callback_data="clear"))

        return answer, keyboard

    async def print_list(self, message: types.Message) -> None:
        text, markup = await self.create_list_page(0)

        await self.bot.send_message(chat_id=message.chat.id, text=text, parse_mode='Markdown', reply_markup=markup)

    async def _process_cluster(self, id: int, chat_id: int) -> None:
        cluster_articles = self.database.get_cluster_by_id(id)

        answer = ""
        keyboard = types.InlineKeyboardMarkup()
        for i, article_info in enumerate(cluster_articles):
            answer += f"#{i} ({article_info[1]}) - " + \
                article_info[2].title + "\n\n"
            keyboard.add(types.InlineKeyboardButton(
                text=f"#{i}", callback_data=self.cd_article.new(article_id=article_info[0])))

        keyboard.add(types.InlineKeyboardButton(
            text="Clear", callback_data="clear"))

        if len(cluster_articles) != 0:
            await self.bot.send_message(chat_id=chat_id, text=answer, reply_markup=keyboard)
        else:
            await self.bot.send_message(chat_id=chat_id, text="Такого кластера вооооообще нет (не существует)! Проверь ID")

    async def print_cluster(self, message: types.Message) -> None:
        if len(message.text.split()) != 2 and not message.text.split()[-1].isnumeric():
            await message.answer("Неправильный формат команды!")
        else:
            await self._process_cluster(int(message.text.split()[-1]), message.chat.id)

    async def process_article_button(self, call: types.CallbackQuery, callback_data: dict) -> None:
        article_id = callback_data.get('article_id')

        self.database.cursor.execute(
            'SELECT * FROM articles WHERE id = %s', (article_id, ))
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(text="Clear", callback_data="clear"))
        data = self.database.cursor.fetchone()
        article = Article(*data[2:7])
        await self.bot.send_message(call.message.chat.id, str(article), parse_mode='Markdown', reply_markup=keyboard)
        await call.answer()

    async def process_list_button(self, call: types.CallbackQuery, callback_data: dict) -> None:
        article_id = int(callback_data.get('page_id'))
        if callback_data.get('version') is None or int(callback_data.get('version')) != self.cluster_version:
            text, markup = \
                "Список актуальных новостей поменялся! Вызови /list повторно", \
                types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(text="Clear", callback_data="clear"))
        else:
            text, markup = await self.create_list_page(article_id)

        await call.message.edit_text(text,  parse_mode='Markdown', reply_markup=markup)
        await call.answer()

    async def process_cluster_button(self, call: types.CallbackQuery, callback_data: dict) -> None:
        cluster_id = int(callback_data.get('cluster_id'))

        await self._process_cluster(cluster_id, call.message.chat.id)
        await call.answer()
