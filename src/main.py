import logging

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, InlineQueryHandler
from rich.logging import RichHandler

import settings
from handlers import (
    handle_message,
    # handle_info,
    handle_clean,
)


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

    # bot.add_handler(CallbackQueryHandler(handle_info, filters.regex('^INFO')))
    bot.add_handler(InlineQueryHandler(handle_clean, filters.regex('clean')))
    bot.add_handler(MessageHandler(handle_message))

    logging.getLogger(__name__).info('Bot is operational')
    bot.run()


if __name__ == '__main__':
    main()
