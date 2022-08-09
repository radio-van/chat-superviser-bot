import logging
from typing import Union

from pyrogram import Client
from pyrogram.types import (
    CallbackQuery,
    Message,
)

import settings
from logic import compare_message_with_recent_messages
from redis import redis_connector


log = logging.getLogger(__name__)


async def handle_message(client: Client, update: Union[CallbackQuery, Message]) -> None:
    log.info('Message!')
    if not isinstance(update, Message):
        log.debug('Not message, skipping')
        return

    if settings.CHECK_ONLY_FORWARDED_MESSAGES and not update.forward_date:
        log.debug('Not forward, skipping')
        return

    if not any((update.caption, update.media, update.text)):
        log.debug('No entities, skipping')
        return

    await compare_message_with_recent_messages(update)


async def handle_clean(client: Client, callback_query: CallbackQuery) -> None:
    await redis_connector.delete_data('recent_messages')
