import asyncio
import logging
from difflib import SequenceMatcher
from typing import Union

from pyrogram import Client
from pyrogram.types import (
    CallbackQuery,
    Message,
)

import settings
from redis import redis_connector


log = logging.getLogger(__name__)


async def handle_message(client: Client, update: Union[CallbackQuery, Message]) -> None:
    if isinstance(update, Message):
        log.debug(f'Checking message {update}')

        # check only messages with text
        if not (text := update.text or update.caption):
            log.debug(f'Message {update} has no text')
            return

        # check only forwarded messages, if defined in settings
        if settings.CHECK_ONLY_FORWARDED_MESSAGES and not update.forward_date:
            log.debug(f'Message {update} is not a forward')
            return

        # load N recent mesages from memory
        recent_messages: list = await redis_connector.get_data('recent_messages')

        # compare text of a new message with N recent messages
        for rm in recent_messages:
            ratio = SequenceMatcher(None, text, rm['text']).ratio()
            if ratio > settings.DUPLICATE_SIMILARITY_THRESHOLD:
                warning_text = f'@{update.from_user.username}, уже было тут ^^^\n\n`similarity: {ratio}`'
                warning_message = await client.send_message(
                    chat_id=update.chat.id,
                    text=warning_text,
                    reply_to_message_id=rm['id'],
                )
                for i in range(0, settings.SELF_DESTRUCTION_TICK_S*10, settings.SELF_DESTRUCTION_TICK_S):
                    await warning_message.edit_text(
                        f'{warning_text}\n`self-destruction in {settings.SELF_DESTRUCTION_TICK_S*10-i}`'
                    )
                    await asyncio.sleep(settings.SELF_DESTRUCTION_TICK_S)

                await warning_message.delete()
                return

        # save message to the list of recents, to compare with future messages
        recent_messages.insert(0, {'id': update.id, 'text': text})
        log.debug(f'Message {update} saved to recent messages')

        # force Redis behave like a stack: old messages are discarded
        if len(recent_messages) > settings.RECENT_MESSAGES_AMOUNT:
            recent_messages.pop()

        # store recent messages list in Redis
        await redis_connector.save_data('recent_messages', recent_messages)
