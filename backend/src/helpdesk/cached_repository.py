from core.redis.client import get_redis_client
from src.helpdesk.client import HelpDeskClient
from src.helpdesk.schemas import RequestSchema
import msgspec



class CachedHelpdeskRepository:
    def __init__(self):
        self.redis = get_redis_client()
        self.hd_client = HelpDeskClient()
        self.encoder = msgspec.json.Encoder()
        self.decoder = msgspec.json.Decoder(type=dict[int, str]) 
        self.cache_key = "hd:state:known_requests"


    async def warmup_cache_all_requests(self):
        state = {}
        async for batch in self.hd_client._iter_all_requests():
            for request in batch:
                state[request.id] = request.technician
        if state:
            payload = msgspec.json.encode(state)
            await self.redis.set("hd:state:known_requests", payload, ex=86400 * 7)
            print(f"Кэш прогрет. Заявок в памяти: {len(state)}")


    async def get_known_requests(self) -> dict[int, str]:
            raw_data = await self.redis.get(self.cache_key)
            if not raw_data:
                return {}
            return self.decoder.decode(raw_data)

    async def update_known_requests(self, current_requests: list[RequestSchema]):
            """Добавляет свежие заявки в кэш, не удаляя старые (накапливает историю)."""
            # Сначала получаем то, что уже есть
            known = await self.get_known_requests()
            
            # Обновляем словарь свежими данными
            for req in current_requests:
                known[req.id] = req.technician
                
            # Перезаписываем кэш с TTL 7 дней
            payload = self.encoder.encode(known)
            await self.redis.set(self.cache_key, payload, ex=86400 * 7)