from redis.asyncio import Redis


class RedisTokenDenylist:
    """Redis реализация TokenDenylist port. Запись `denylist:<jti>` с
    TTL равным остатку жизни access-токена. Когда токен истекает —
    запись очищается автоматически Redis-ом."""

    KEY_PREFIX = "denylist:"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add(self, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        await self._redis.set(self.KEY_PREFIX + jti, "1", ex=ttl_seconds)

    async def contains(self, jti: str) -> bool:
        return bool(await self._redis.exists(self.KEY_PREFIX + jti))
