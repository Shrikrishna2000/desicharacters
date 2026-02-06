# backend/app/storage/redis_client.py

from redis.asyncio import Redis
from fastapi import HTTPException
from app.config.settings import get_settings

settings = get_settings()

class RedisClient:
    def __init__(self):
        self.client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE
        )

    async def health_check(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def get(self, key: str):
        try:
            return await self.client.get(key)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Redis GET failed: {str(e)}")

    async def set(self, key: str, value: str, expire: int | None = None, ex: int | None = None):
        try:
            ttl = ex if ex is not None else expire

            if ttl:
                await self.client.set(key, value, ex=ttl)
            else:
                await self.client.set(key, value)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Redis SET failed: {str(e)}")

    async def delete(self, key: str):
        try:
            await self.client.delete(key)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Redis DELETE failed: {str(e)}")


redis_client = RedisClient()