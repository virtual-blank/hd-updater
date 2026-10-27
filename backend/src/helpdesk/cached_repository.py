from core.redis.client import get_redis_client
from src.helpdesk.client import HelpDeskClient
from src.helpdesk.schemas import RequestSchema
import msgspec
import logging


log = logging.getLogger(__name__)


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
            redis_size_bytes = await self.redis.memory_usage(self.cache_key) or 0
            redis_size_mb = redis_size_bytes / (1024*1024)
            log.info(
                f"Cache warmed up. Requests in RAM: {len(state)}\n"
                f"Total Redis capacity: {redis_size_bytes}B | {redis_size_mb}MB"
                )




    async def get_known_requests(self) -> dict[int, str]:
            raw_data = await self.redis.get(self.cache_key)
            if not raw_data:
                return {}
            return self.decoder.decode(raw_data)

    async def update_known_requests(self, current_requests: list[RequestSchema]):
            known = await self.get_known_requests()
            
            for req in current_requests:
                known[req.id] = req.technician
                
            payload = self.encoder.encode(known)
            await self.redis.set(self.cache_key, payload, ex=86400 * 7) 