import asyncio
import logging
import re
from difflib import SequenceMatcher
from typing import Union

from pyrogram import Client

import settings
from models import RecentMessage
from redis import redis_connector


log = logging.getLogger(__name__)


async def get_messages_similarity_ratio(target_msg: RecentMessage, source_msg: RecentMessage) -> float:
    # TODO write compare method to dataclass
    gallery_ratio = await _compare_gallery(target_msg.media_group_id, source_msg.media_group_id)
    media_ratio = await _compare_media(target_msg.media_id, source_msg.media_id)
    link_ratio = await _compare_link(target_msg.link, source_msg.link)
    text_ratio = await _compare_text(target_msg.text, source_msg.text)

    log.debug(f'Ratios:\ngallery - {gallery_ratio}\nmedia - {media_ratio}\nlink - {link_ratio}\ntext - {text_ratio}')

    effective_ratios = [r for r in (gallery_ratio, media_ratio, link_ratio, text_ratio) if r > 0]

    log.debug(f'Effective ratios: {effective_ratios}')

    if effective_ratios:
        return sum(effective_ratios)/len(effective_ratios)

    return 0


async def _compare_gallery(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    if target == source:
        return 1.0

    # TODO get galleries by id and compare each media in it
    return 0


async def _compare_link(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    if target == source:
        return 1.0
    return 0


async def _compare_media(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    if target == source:
        return 1.0

    # TODO download and compare files themselves
    return 0


async def _compare_text(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    if any(map(lambda txt: len(txt.split(' ')) < settings.MESSAGE_LENGTH_WORDS_THRESHOLD, (target, source))):
        log.debug(f'Texts of {target} | {source} are too short, skip')
        return 0

    return SequenceMatcher(None, target, source).ratio()
