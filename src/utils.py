import logging
from difflib import SequenceMatcher

import settings


log = logging.getLogger(__name__)


async def compare_gallery(target: str, source: str) -> float:
    log.debug('Compare galleries, %s and %s', target, source)
    if not all((target, source)):
        return 0.0

    if target == source:
        log.debug('Galleries are the same!')
        return 1.0

    # TODO get galleries by id and compare each media in it

    # both msg are not galleries, or target is a gallery
    return 0.0


async def compare_link(target: str, source: str) -> float:
    log.debug('Compare links, %s and %s', target, source)
    if not all((target, source)):
        return 0.0

    if target == source:
        log.debug('Links are the same!')
        return 1.0

    return 0.0


async def compare_media(target: str, source: str) -> float:
    log.debug('Compare media, %s and %s', target, source)
    if not all((target, source)):
        return 0.0

    if target == source:
        log.debug('Medias are the same!')
        return 1.0

    # TODO download and compare files themselves

    return 0.0


async def compare_text(target: str, source: str) -> float:
    log.debug('Compare texts, %s and %s', target, source)
    if any(map(lambda txt: len(txt.split(' ')) < settings.MESSAGE_LENGTH_WORDS_THRESHOLD, (target, source))):
        log.debug('Texts are too short')
        return 0.0

    return SequenceMatcher(None, target, source).ratio()
