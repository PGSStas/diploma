import typing as tp
import os
import telebot
from telebot import types
from .database import Database, Article
import sys
sys.path.append('/root/diploma')


SPLIT_STRING = "\n>================================<\n"


class MessageHandler:
    def __init__(self):
        self.database = Database(os.environ['PG_PASSWORD'])

        self.bot = telebot.TeleBot(os.environ['BOT_TOKEN'])

        # self.cd_list = CallbackData("cd_list", "page_id")
        # self.cd_cluster = CallbackData("cd_cluster", "cluster_id")
        # self.cd_article = CallbackData("cd_article", "article_id")

        # self.list_of_clusters = []
        self.map_of_clusters: tp.Dict[int, tp.List[any]] = {}

    def welcome_message(self, message: types.Message) -> None:
        self.bot.send_message(
            message.chat.id,
            "Привет!\nЯ Newsgregator, бот, который собирает для тебя новости мира IT, автопрома, игровой индустрии и кинематографа!\n"
            "Чтобы узнать как использовать меня почитай /help 😄",
            reply_to_message_id=message.id)

    def help_message(self, message: types.Message) -> None:
        self.bot.send_message(
            message.chat.id,
            "/help - помощь\n"
            "/list - последние треды новостей за 24 часа, в которых 2 и более артикля. Остальные я считаю нерелевантными :(\n"
            "/detail [id] - расписать подробнее кластер новостей с определенным ID\n",
            reply_to_message_id=message.id)

    def create_list_page(self, user_id: int, id: int) -> tp.Tuple[str, types.InlineKeyboardMarkup]:
        list_of_clusters = self.map_of_clusters[user_id]

        first_index = id * 8
        last_index = min(len(list_of_clusters), (id + 1)*8)

        keyboard = types.InlineKeyboardMarkup()

        if id != 0:
            keyboard.add(types.InlineKeyboardButton(
                text=f"<<", callback_data=f'page_id={id - 1}'))

        info_slice = []
        for i, cluster in enumerate(list_of_clusters[first_index:last_index]):
            entry = f"#{first_index + i + 1}. {cluster[3]} `/detail {cluster[0]}`"
            # entry = f"#{first_index + i + 1}. {cluster[3]}"
            info_slice.append(entry)
            keyboard.add(types.InlineKeyboardButton(
                text=f"Группа {first_index + i + 1}", callback_data=f'cluster_id={first_index + i}'))

        answer = SPLIT_STRING.join(info_slice)

        if len(list_of_clusters) // 8 > id:
            keyboard.add(types.InlineKeyboardButton(
                text=f">>", callback_data=f'page_id={id + 1}'))

        keyboard.add(types.InlineKeyboardButton(
            text="Clear", callback_data="clear"))

        return answer, keyboard

    def print_list(self, message: types.Message) -> None:
        user_id = message.from_user.id
        self.map_of_clusters[user_id] = self.database.get_cluster_titles()

        text, markup = self.create_list_page(user_id, 0)

        self.bot.send_message(chat_id=message.chat.id, text=text,
                              parse_mode='Markdown', reply_markup=markup)

    def _process_cluster(self, id: int, chat_id: int) -> None:
        cluster_articles = self.database.get_cluster_by_id(id)

        answer = ""
        keyboard = types.InlineKeyboardMarkup()
        for i, article_info in enumerate(cluster_articles):
            answer += f"#{i} ({article_info[1]}) - " + \
                article_info[2].title + "\n\n"
            keyboard.add(types.InlineKeyboardButton(
                text=f"#{i}", callback_data=f'article_id={article_info[0]}'))

        keyboard.add(types.InlineKeyboardButton(
            text="Clear", callback_data="clear"))

        if len(cluster_articles) != 0:
            self.bot.send_message(
                chat_id=chat_id, text=answer, reply_markup=keyboard)
        else:
            self.bot.send_message(
                chat_id=chat_id, text="Такого кластера вооооообще нет (не существует)! Проверь ID")

    def print_cluster(self, message: types.Message) -> None:
        if len(message.text.split()) != 2 and not message.text.split()[-1].isnumeric():
            message.answer("Неправильный формат команды!")
        else:
            self._process_cluster(
                int(message.text.split()[-1]), message.chat.id)

    def process_article_button(self, call: types.CallbackQuery) -> None:
        article_id = call.data.split('=')[1]

        self.database.cursor.execute(
            'SELECT * FROM articles WHERE id = %s', (article_id, ))
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(text="Clear", callback_data="clear"))
        data = self.database.cursor.fetchone()
        article = Article(*data[2:7])
        self.bot.send_message(call.message.chat.id, str(
            article), parse_mode='Markdown', reply_markup=keyboard)
        self.bot.answer_callback_query(call.id)

    def process_list_button(self, call: types.CallbackQuery) -> None:
        article_id = int(call.data.split('=')[1])

        text, markup = self.create_list_page(call.from_user.id, article_id)

        self.bot.edit_message_text(text, chat_id=call.message.chat.id,
                                   message_id=call.message.id, parse_mode='Markdown', reply_markup=markup)
        self.bot.answer_callback_query(call.id)

    def process_cluster_button(self, call: types.CallbackQuery) -> None:
        user_id = call.from_user.id
        cluster_id = self.map_of_clusters[user_id][int(
            call.data.split('=')[1])][0]

        self._process_cluster(cluster_id, call.message.chat.id)
        self.bot.answer_callback_query(call.id)
