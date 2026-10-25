from redis.asyncio import Redis
from core.config import get_redis_settings

#redis = Redis.from_url(url=get_redis_settings().url, decode_responses=False)

r = Redis.from_url()