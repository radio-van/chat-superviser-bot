import datetime
import logging
import re
from dataclasses import asdict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.types import (
    # InlineKeyboardButton,
    # InlineKeyboardMarkup,
    Message,
)

import settings
from models import Ratio, RecentMessage
from redis import redis_connector
from utils import (
    compare_gallery,
    compare_link,
    compare_media,
    compare_text,
)


emoji_pattern = re.compile(
    "["
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "]+", flags=re.UNICODE)
log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
scheduler.start()


async def convert_tg_message_to_RecentMessage(message: Message):
    """
    Key idea is to store as minimal neccessary message attributes as possible
    for security reasons.
    This func 'converts' Telegram Message data to a dataclass with fields only
    relevant for comparison.
    """
    log.debug('Parsing link from "%s"', message.text or message.caption)
    link_match = re.match(r'https*:\/\/\S+', message.text or message.caption or '')

    return RecentMessage(
        id=message.id,
        link=link_match.group() if link_match else None,
        media_id=getattr(message, message.media.value).file_unique_id if message.media else None,
        media_group_id=message.media_group_id,
        text=emoji_pattern.sub(r'', message.text or message.caption or '')  # clean-up emoji
    )


async def compare_message_with_recent_messages(message: Message) -> None:
    """
    Main comparison logic.
    It loads N recent messages from cache and sequentally do several things:
    - check if message attributes are same in form of ratio number
    - build relation graph between messages with those ratios
    - if some ratios are above threshold:
      - warn the user
      - update a counter for the user (for statistics purposes)
      - schedule warning message deletion to keep chat clean
    - puts message to stash
    - pop last message from stash stack
    """
    recent_messages: list(dict) = await redis_connector.get_data('recent_messages') or []

    target_message = await convert_tg_message_to_RecentMessage(message)

    for rm in recent_messages:
        recent_message = RecentMessage(**rm)  # convert dict to dataclass

        ratio: Ratio = await get_ratios(target_message, recent_message)
        log.debug('Ratio: %s, effective - %s', ratio, ratio.effective)

        # save relation graph
        recent_message.relation_graph[target_message.id] = target_message.relation_graph[recent_message.id] = {
            'effective': ratio.effective,
            'gallery': ratio.gallery,
            'link': ratio.link,
            'media': ratio.media,
            'text': ratio.text,
        }

        if ratio.effective > settings.DUPLICATE_SIMILARITY_THRESHOLD:
            target_message.duplicate_of = []
            recent_message.has_duplicate = []

            target_message.duplicate_of = target_message.duplicate_of.append(recent_message.id)
            recent_message.has_duplicate = recent_message.has_duplicate.append(target_message.id)

    warning_text = None

    # yeah, it's again a loop through all recent messages, but it's the just easiest way
    for rm in recent_messages:
        recent_message = RecentMessage(**rm)  # convert dict to dataclass

        ratio: Ratio = await get_ratios(target_message, recent_message)

        """
        If text is similar additional check is required, because new message can be an
        'extension' of a previous one, e.g. has media (or more medias).
        In this case consider the message as a duplicate but change warn text to indicate
        that it's probably not a pure duplicate.
        """
        if ratio.link > settings.DUPLICATE_SIMILARITY_THRESHOLD:
            warning_text = f'@{message.from_user.username}, такая ссылка уже была тут 👆'
        elif ratio.text > settings.DUPLICATE_SIMILARITY_THRESHOLD:
            if target_message.media_id and not recent_message.media_id:
                warning_text = f'@{message.from_user.username}, похожий текст уже был тут 👆,\nно без вложения.'

            if target_message.media_group_id and not recent_message.media_group_id:
                # TODO check gallery length
                warning_text = f'@{message.from_user.username}, похожий текст уже был тут 👆,\nно без вложений.'
        elif ratio.effective > settings.DUPLICATE_SIMILARITY_THRESHOLD:
            warning_text = f'@{message.from_user.username}, по совокупности параметров, похоже, что уже был тут 👆'

        # message considered as duplicate
        if warning_text:
            # warn user
            warning_message = await message.reply(
                text=(
                    f'{warning_text}\n\n```'
                    '----- debug -----\n\n'
                    f'галерея {ratio.gallery}\n'
                    f'ссылка {ratio.link}\n'
                    f'вложение {ratio.media}\n'
                    f'текст {ratio.text}\n\n'
                    f'итоговый {ratio.effective}\n'
                    '```'
                ),
                reply_to_message_id=recent_message.id,
                # reply_markup=await keyboard(suspected_msg_id=message.id),
            )

            # record user sent a duplicate
            await update_user_duplicate_count(user_id=message.from_user.id)

            # destroy duplication warning after given time
            start_time: datetime.datetime = datetime.datetime.now()\
                + datetime.timedelta(seconds=settings.SELF_DESTRUCTION_S)
            scheduler.add_job(
                message_self_destruction,
                id=f'self_destruction-{warning_message.id}',
                name='Destroy message',
                next_run_time=start_time,
                kwargs={'message': warning_message},
            )
            break  # stop loop if first duplicate found

    # save message to the list of recents, to compare with future messages
    recent_messages.insert(0, asdict(target_message))

    # force Redis behave like a stack: old messages are discarded
    if len(recent_messages) > settings.RECENT_MESSAGES_AMOUNT:
        recent_messages.pop()

    # store recent messages list in Redis
    await redis_connector.save_data('recent_messages', recent_messages)


async def update_user_duplicate_count(user_id: int) -> None:
    """
    Load and increment 'duplicates' counter for a given user.
    """
    # get previous count
    duplication_count_for_user: int = await redis_connector.get_data(
        f'duplication_count_for_{user_id}'
    ) or 0

    # increment counter
    await redis_connector.save_data(
        f'duplication_count_for_{user_id}',
        duplication_count_for_user + 1
    )


async def message_self_destruction(message: Message) -> None:
    """
    Destroys a given message.
    """
    # TODO add animation
    await message.delete()


async def get_ratios(target_message: RecentMessage, recent_message: RecentMessage) -> Ratio:
    # compare various messages attributes
    ratio = Ratio(
        gallery=await compare_gallery(target_message.media_group_id, recent_message.media_group_id),
        media=await compare_media(target_message.media_id, recent_message.media_id),
        link=await compare_link(target_message.link, recent_message.link),
        text=await compare_text(target_message.text, recent_message.text),
    )

    return ratio

'''
async def keyboard(message: Message, effective_ratio: float, gallery_ratio: float,
                   link_ratio: float, media_ratio: float, text_ratio: float) -> InlineKeyboardMarkup:

async def show_info(client: Client, callback_query: CallbackQuery) -> None:
    await callback_query.message.edit_text(
        text=(
            f'{message.text}\n\n```'
            '----- debug -----\n\n'
            f'галерея {gallery_ratio}\n'
            f'ссылка {link_ratio}\n'
            f'вложение {media_ratio}\n'
            f'текст {text_ratio}\n\n'
            f'итоговый {effective_ratio}\n'
            '```'
        ))
'''
