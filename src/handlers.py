import asyncio
import logging
import re
from dataclasses import asdict
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


async def _get_keyboard(suspected_msg_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton('Наказать бота', callback_data=f'PUNISHMENT-{suspected_msg_id}')]
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

    # unify fields
    link_match = re.match(r'https*:\/\/\S+', update.text or update.caption)
    target_message = RecentMessage(
        id=update.id,
        link=link_match.group() if link_match else None,
        media_id=getattr(update, update.media.value).file_unique_id if update.media else None,
        media_group_id=update.media_group_id,
        text=emoji_pattern.sub(r'', update.text or update.caption)  # clean-up emoji
    )
    # load N recent mesages from memory
    recent_messages: list = await redis_connector.get_data('recent_messages') or []

    # compare text of a new message with N recent messages
    for rm in recent_messages:
        recent_message = RecentMessage(**rm)
        ratio = await get_messages_similarity_ratio(target_message, recent_message)
        if ratio > settings.DUPLICATE_SIMILARITY_THRESHOLD:
            warning_text = f'@{update.from_user.username}, уже было тут 👆\n\n```similarity ratio: {ratio}\nwill be deleted after {settings.SELF_DESTRUCTION_S} sec```'
            warning_message = await client.send_message(
                chat_id=update.chat.id,
                text=warning_text,
                reply_to_message_id=recent_message.id,
                reply_markup=await _get_keyboard(suspected_msg_id=update.id),
            )

            redis_duplication_context_key = f'duplication_context_for_{update.id}'
            await redis_connector.save_data(redis_duplication_context_key, {
                'sample': asdict(recent_message),
                'update': asdict(target_message),
            })

            # store user, who posted a duplicate
            duplication_count_for_user: int = await redis_connector.get_data(
                f'duplication_count_for_{update.from_user.id}'
            ) or 0
            await redis_connector.save_data(
                f'duplication_count_for_{update.from_user.id}',
                duplication_count_for_user + 1
            )

            # destroy duplication warning after given time
            await asyncio.sleep(settings.SELF_DESTRUCTION_S)
            await warning_message.delete()
            await redis_connector.delete_data(redis_duplication_context_key)

            return

    # save message to the list of recents, to compare with future messages
    recent_messages.insert(0, asdict(target_message))

    # force Redis behave like a stack: old messages are discarded
    if len(recent_messages) > settings.RECENT_MESSAGES_AMOUNT:
        recent_messages.pop()

    # store recent messages list in Redis
    await redis_connector.save_data('recent_messages', recent_messages)


async def handle_punishment(client: Client, callback_query: CallbackQuery) -> None:
    incorrectly_marked_message_id = callback_query.data.split('-')[1]
    redis_key = f'duplication_context_for_{incorrectly_marked_message_id}'
    context = await redis_connector.get_data(redis_key)

    log.warning(f'Incorrect similarity check for message {incorrectly_marked_message_id}, context: {context}')

    await callback_query.message.edit_reply_markup()
    await redis_connector.delete_data(redis_key)


async def handle_clean(client: Client, callback_query: CallbackQuery) -> None:
    await redis_connector.delete_data('recent_messages')
