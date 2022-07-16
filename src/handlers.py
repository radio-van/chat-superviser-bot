import asyncio
import logging
import re
from difflib import SequenceMatcher
from typing import Union

from pyrogram import Client
from pyrogram.types import (
    CallbackQuery,
    Message,
)

import settings
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


async def handle_message(client: Client, update: Union[CallbackQuery, Message]) -> None:
    if not await _should_message_be_compared(update):
        return

    log.debug(f'Checking message {update.id}')

    # TODO implement media compare
    # if update.media:
    #    compare_strategy = _are_media_same

    text = update.text or update.caption

    if 'http' in text and settings.CHECK_LINKS:
        log.debug('Compare strategy - exact')
        compare_strategy = _are_same
        target_entity = re.findall(r'https*:\/\/\S+', text)[0]
    else:
        log.debug('Compare strategy - ratio')
        compare_strategy = _are_semi_same
        target_entity = emoji_pattern.sub(r'', text)  # clean-up emoji

    # load N recent mesages from memory
    recent_messages: list = await redis_connector.get_data('recent_messages') or []

    # compare text of a new message with N recent messages
    for rm in recent_messages:
        if await compare_strategy(target_entity, rm['text']):
            warning_text = f'@{update.from_user.username}, уже было тут 👆'

            # if message 'extends' original with media, it's a semi-duplicate
            if update.media and not rm.get('has_media'):
                warning_text = f'@{update.from_user.username}, было тут 👆, но без медиа'

            warning_message = await client.send_message(
                chat_id=update.chat.id,
                text=warning_text,
                reply_to_message_id=rm['id'],
            )

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
            for i in range(
                0, total_self_destruction_time, SELF_DESTRUCTION_TICK_S
            ):
                await asyncio.sleep(SELF_DESTRUCTION_TICK_S)
                await warning_message.edit_text(
                    f'{warning_text}\n`self-destruction in {total_self_destruction_time-i}`'
                )

            await warning_message.delete()

            return

    # save message to the list of recents, to compare with future messages
    recent_messages.insert(0, {'id': update.id, 'text': text, 'has_media': bool(update.media)})
    log.debug(f'Message {update.id} saved to recent messages')

    # force Redis behave like a stack: old messages are discarded
    if len(recent_messages) > settings.RECENT_MESSAGES_AMOUNT:
        recent_messages.pop()

        # store recent messages list in Redis
        await redis_connector.save_data('recent_messages', recent_messages)


async def _should_message_be_compared(update: Union[CallbackQuery, Message]) -> bool:
    if not isinstance(update, Message):
        log.debug(f'Update {update.id} is not a message, skip')
        return

    # check only messages with text
    if not (text := update.caption or update.text):
        log.debug(f'Message {update.id} has no comparable entities')
        return

    if 'http' in text and settings.CHECK_LINKS:
        log.debug(f'Message {update.id} contains link, checking...')
        return True

    if settings.CHECK_ONLY_FORWARDED_MESSAGES and not update.forward_date:
        log.debug(f'Message {update.id} is not a forward, skip')
        return

    if len(text.split(' ')) < settings.MESSAGE_LENGTH_WORDS_THRESHOLD:
        log.debug(f'Message {update.id} is too short, skip')
        return

    return True


async def _are_same(new: str, sample: str) -> bool:
    log.debug(f'Exact compare {new} with {sample}')
    return bool(new == sample)


async def _are_semi_same(new: str, sample: str) -> bool:
    ratio = SequenceMatcher(None, new, sample).ratio()
    return bool(ratio > settings.DUPLICATE_SIMILARITY_THRESHOLD)


async def _are_media_same(new, sample) -> bool:
    # TODO implement
    pass
