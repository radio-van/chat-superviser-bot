import asyncio_redis
import json
import logging
from typing import Any

import settings


log = logging.getLogger(__name__)


class RedisConnector():
    _connection = None

    @property
    async def connection(self):
        if not self._connection:
            self._connection = await asyncio_redis.Connection.create(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
            )
            log.debug('Created connection for Redis:\n%s:%s', settings.REDIS_HOST, settings.REDIS_PORT)
        return self._connection

    async def get_data(self, key: str) -> list:
        data = await (await self.connection).get(key)

        log.debug(f'REDIS DATA FOR KEY {key}: {data}')

        if data:
            return json.loads(data)
        return []

    async def save_data(self, key: str, data: Any) -> None:
        await (await self.connection).set(key, json.dumps(data))


redis_connector = RedisConnector()
