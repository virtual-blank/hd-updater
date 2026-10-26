from redis.asyncio import Redis
from core.config import get_redis_settings
from functools import lru_cache


@lru_cache
def get_redis_client():
    return Redis.from_url(url=get_redis_settings().url, decode_responses=False)
