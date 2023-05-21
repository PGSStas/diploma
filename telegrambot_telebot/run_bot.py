from aiogram.utils import executor
from newsgregator.dispatcher import message_handler

import logging


# webhook settings
WEBHOOK_URL = f"https://64e1-2a03-6f00-4-00-8f0.ngrok-free.app"

# webserver settings
WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 7500

# logging
logging.basicConfig(level=logging.INFO)


async def on_startup(dp):
    logging.info('Start webhook')
    # await message_handler.bot.set_webhook(WEBHOOK_URL)
    logging.info('Done setting webhook')


async def on_shutdown(dp):
    logging.warning('Shutting down..')

    await message_handler.bot.delete_webhook()

    logging.warning('Bye!')


def main():
    # executor.start_webhook(
    #     dispatcher=message_handler.dispatcher,
    #     webhook_path="",
    #     on_startup=on_startup,
    #     on_shutdown=on_shutdown,
    #     skip_updates=True,
    #     host=WEBAPP_HOST,
    #     port=WEBAPP_PORT,
    # )
    # executor.start_polling(message_handler.dispatcher, on_startup=on_startup)
    message_handler.bot.infinity_polling()


if __name__ == '__main__':
    main()
