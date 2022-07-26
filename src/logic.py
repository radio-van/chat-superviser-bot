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


async def get_messages_similarity_ratio(target_msg: Message, source_msg: Message) -> float:
    gallery_ratio = await _compare_gallery(target_msg.media_group_id, source_msg.media_group_id)
    media_ratio = await _compare_media(target_msg.media, source_msg.media_id)

    target_text = target_msg.text or target_msg.caption

    link_ratio = await _compare_link(re.findall(r'https*:\/\/\S+', target_text)[0], source_msg.text)
    text_ratio = await _compare_text(target_text, source_msg.text)

    effective_ratios = [r for r in (gallery_ratio, media_ratio, link_ratio, text_ratio) if r > 0]
    if effective_ratios:
        return sum(effective_ratios)/len(effective_ratios)

    return 0


async def _compare_gallery(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    print(f'\n\nCOMPARING gallery {target} with {source}\n\n')
    if target== source:
        return 1.0

    # TODO get galleries by id and compare each media in it


async def _compare_link(target: str, source: str) -> float:
    print(f'\n\nCOMPARING link {target} with {source}\n\n')
    return bool(target in source)


async def _compare_media(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    print(f'\n\nCOMPARING media {target} with {source}\n\n')
    if target == source:
        return 1.0

    # TODO download and compare files themselves


async def _compare_text(target: str, source: str) -> float:
    if not all((target, source)):
        return 0

    if any(map(lambda txt: len(txt.split(' ')) < settings.MESSAGE_LENGTH_WORDS_THRESHOLD, (target, source))):
        log.debug(f'Texts of {target} | {source} are too short, skip')
        return 0

    print(f'\n\nCOMPARING text {target} with {source}\n\n')
    return SequenceMatcher(None, target, source).ratio()
