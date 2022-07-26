import asyncio_redis
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

import settings


log = logging.getLogger(__name__)


class RedisConnector():
    _connection = None

    @property
    async def connection(self):
        if not self._connection:
            log.info('Connecting for Redis: %s:%s...', settings.REDIS_HOST, settings.REDIS_PORT)
            self._connection = await asyncio_redis.Connection.create(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
            )
        return self._connection

    async def get_data(self, key: str) -> Optional[list]:
        data = await (await self.connection).get(key)
        if data:
            return json.loads(data)

    async def save_data(self, key: str, data: Any) -> None:
        await (await self.connection).set(key, json.dumps(
            asdict(data) if is_dataclass(data) else data))

    async def delete_data(self, key: str) -> None:
        await (await self.connection).delete([key])


redis_connector = RedisConnector()
