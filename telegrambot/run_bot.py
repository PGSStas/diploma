import asyncio
import datetime
import logging
import subprocess

import aioschedule
import ngrok
from aiogram.utils import executor
from newsgregator.dispatcher import message_handler

# webserver settings
WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 7500

# logging
logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------------------------------


def update_news():
    list_of_clusters = message_handler.database.get_cluster_titles()
    if message_handler.list_of_clusters != list_of_clusters:
        message_handler.cluster_version = int(
            datetime.datetime.now().timestamp())
    message_handler.list_of_clusters = list_of_clusters


async def download_news():
    logging.info('Start for download news')
    log_name = str(int(datetime.datetime.now().timestamp()))
    with open(f'/root/diploma/run_logs/{log_name}_download', 'w') as f:
        subprocess.Popen('python3 site_scraper/news_scraper/run_scraper.py',
                         cwd="/root/diploma", stdout=f, stderr=f, shell=True).wait()
    with open(f'/root/diploma/run_logs/{log_name}_train', 'w') as f:
        subprocess.Popen('python3 clusterize/start_clusterize.py --retrain',
                         cwd="/root/diploma", stdout=f, stderr=f, shell=True).wait()

    update_news()
    logging.info('News downloaded')



async def scheduler():
    aioschedule.every(3).hours.do(download_news)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


# ----------------------------------------------------------------------------


async def on_startup(_):
    logging.info('Start webhook')
    
    webhook_url = await create_tunnel()
    await message_handler.bot.set_webhook(webhook_url)
    asyncio.create_task(scheduler())

    logging.info('Done setting webhook')


async def on_shutdown(_):
    logging.warning('Shutting down..')

    await message_handler.bot.delete_webhook()

    logging.warning('Bye!')


async def create_tunnel():
    # Uncomment after NGROK license bought (im just poor student :()

    # session = await ngrok.NgrokSessionBuilder().authtoken_from_env().connect()
    # tunnel = await session.http_endpoint().listen()
    # logging.info(f"Ingress established at {tunnel.url()}")
    # tunnel.forward_tcp(f"{WEBAPP_HOST}:{WEBAPP_PORT}")

    # return tunnel.url()

    return 'https://97ee-2a03-6f00-4-00-8f0.ngrok-free.app'

def main():
    executor.start_webhook(
        dispatcher=message_handler.dispatcher,
        webhook_path="",
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )


if __name__ == '__main__':
    main()
