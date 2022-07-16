import logging

from pyrogram import Client
from pyrogram.handlers import MessageHandler
from rich.logging import RichHandler

import settings
from handlers import handle_message


def main() -> None:

    # set up logging
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format='%(name)s - %(message)s',
                        handlers=[RichHandler(rich_tracebacks=True)])

    # disable annoying logs
    logging.getLogger('asyncio_redis').setLevel(logging.WARNING)
    logging.getLogger('pyrogram').setLevel(logging.WARNING)

    bot = Client(
        'ChatSuperviserBot',
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        bot_token=settings.BOT_TOKEN,
    )

    bot.add_handler(MessageHandler(handle_message))

    logging.getLogger(__name__).info('Bot is operational')
    bot.run()


if __name__ == '__main__':
    main()
