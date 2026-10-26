from core.redis.client import get_redis_client
from core.config import get_redis_settings
from src.users.repository import UserRepository
from src.users.schemas import UserProfileCache
import msgspec

TTL = get_redis_settings().ttl


class CachedUserRepository:
    def __init__(self):
        self.redis = get_redis_client()
        self.ttl = TTL
        self.encoder = msgspec.json.Encoder()
        # Декодер ждет список профилей
        self.decoder = msgspec.json.Decoder(type=list[UserProfileCache])
        self.cache_key = "bot:users:profiles"

    async def save_users(self, profiles: list[UserProfileCache]):
        """Сохраняет плоский список профилей в Redis."""
        payload = self.encoder.encode(profiles)
        await self.redis.set(self.cache_key, payload)

    async def get_users(self) -> list[UserProfileCache]:
        """Быстро достает профили для поллинга."""
        raw_data = await self.redis.get(self.cache_key)
        if not raw_data:
            return []
        return self.decoder.decode(raw_data)