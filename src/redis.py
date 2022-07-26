import asyncio_redis
import json
import logging
from typing import Any, Optional

import settings


log = logging.getLogger(__name__)


class RedisConnector():
    _connection = None

    @property
    async def connection(self):
        if not self._connection:
            log.info('Connecting to Redis: %s:%s...', settings.REDIS_HOST, settings.REDIS_PORT)
            self._connection = await asyncio_redis.Connection.create(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
            )
            log.info(f'Connection created: {self._connection}')
        return self._connection

    async def get_data(self, key: str) -> Optional[list]:
        data = await (await self.connection).get(key)
        if data:
            return json.loads(data)

    async def save_data(self, key: str, data: Any) -> None:
        await (await self.connection).set(key, json.dumps(data))

    async def delete_data(self, key: str) -> None:
        await (await self.connection).delete([key])


redis_connector = RedisConnector()
