from core.redis.client import redis
from core.config import get_redis_settings
from src.users.repository import UserRepository

TTL = get_redis_settings().ttl

class CachedUserRepository:
    def __init__(self, repo: UserRepository):
        self.repo = repo
        self.redis=redis
        self.ttl=TTL

    