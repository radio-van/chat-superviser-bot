import asyncio
import logging
import re
from difflib import SequenceMatcher
from typing import Union

from pyrogram import Client
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import settings
# from jobs import scheduler
from logic import get_messages_similarity_ratio
from models import RecentMessage
from redis import redis_connector


emoji_pattern = re.compile(
    "["
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "]+", flags=re.UNICODE)
log = logging.getLogger(__name__)


SELF_DESTRUCTION_TICK_S = 5


async def _get_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton('Наказать бота', callback_data='PUNISHMENT')]
    ]
    return InlineKeyboardMarkup(buttons)


async def handle_message(client: Client, update: Union[CallbackQuery, Message]) -> None:
    log.debug(f'Checking message {update.id}')

    if not isinstance(update, Message):
        log.debug(f'Update {update.id} is not a message, skip')
        return

    if settings.CHECK_ONLY_FORWARDED_MESSAGES and not update.forward_date:
        log.debug(f'Message {update.id} is not a forward, skip')
        return

    if not any((update.caption, update.media, update.text)):
        log.debug(f'Message {update.id} has no comparable entities')
        return

    # load N recent mesages from memory
    recent_messages: list = await redis_connector.get_data('recent_messages') or []

    # compare text of a new message with N recent messages
    for rm in recent_messages:
        if (ratio := await get_messages_similarity_ratio(
            update,
            RecentMessage(**rm),
        ) > settings.DUPLICATE_SIMILARITY_THRESHOLD):
            warning_message = await client.send_message(
                chat_id=update.chat.id,
                text=f'@{update.from_user.username}, уже было тут 👆\n\n__similarity ratio: {ratio}__',
                reply_to_message_id=rm['id'],
            )

            redis_duplication_context_key = f'duplication_stats_for_{update.id}'
            await redis_connector.save_data(redis_duplication_context_key, {'update': update, 'sample': rm})

            # store user, who posted a duplicate
            duplication_count_for_user: int = await redis_connector.get_data(
                f'duplication_count_for_{update.from_user.id}'
            ) or 0
            await redis_connector.save_data(
                f'duplication_count_for_{update.from_user.id}',
                duplication_count_for_user + 1
            )

            # destroy duplication warning after given time, show timer in warning message
            total_self_destruction_time = SELF_DESTRUCTION_TICK_S*settings.SELF_DESTRUCTION_MULTIPLIER
            for i in range(0, total_self_destruction_time, SELF_DESTRUCTION_TICK_S):
                await asyncio.sleep(SELF_DESTRUCTION_TICK_S)
                await warning_message.edit_text(
                    f'{warning_text}\n`self-destruction in {total_self_destruction_time-i}`'
                )

            await warning_message.delete()
            await redis_connector.delete_data(redis_duplication_context_key)

            return

    # save message to the list of recents, to compare with future messages
    recent_messages.insert(0,
                           RecentMessage(
                               id=update.id,
                               media_id=update.media.id if update.media else None,
                               media_group_id=update.media_group_id,
                               text=update.text or update.caption,
                           ))

    # force Redis behave like a stack: old messages are discarded
    if len(recent_messages) > settings.RECENT_MESSAGES_AMOUNT:
        recent_messages.pop()

        # store recent messages list in Redis
        await redis_connector.save_data('recent_messages', recent_messages)


async def handle_punishment(client: Client, update: CallbackQuery) -> None:
    incorrectly_marked_message_id = callback_query.message.reply_to_message.id
    redis_key = f'duplication_context_for_{incorrectly_marked_message_id}'
    context = await redis_connector.get_data(redis_key)

    log.warning(f'Incorrect similarity check for message {incorrectly_marked_message_id}, context: {context}')

    await redis_connector.delete_data(redis_key)
