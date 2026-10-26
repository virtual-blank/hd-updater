from httpx import AsyncClient, HTTPError, Timeout
import msgspec
from functools import lru_cache

from core.config import get_hd_settings
from src.helpdesk.schemas import RequestSchema, SdpResponseSchema, RequestFullSchema
from src.helpdesk.exceptions import HelpDeskAPIError




class HelpDeskClient:
    def __init__(self) -> None:
        settings = get_hd_settings()
        self._endpoint = settings.endpoint
        self._admin_api_key = settings.admin_api_key
        self._decoder = msgspec.json.Decoder(type=SdpResponseSchema)
        self._encoder = msgspec.json.Encoder()
        self.client = AsyncClient(
                verify=False,
                http2=True,
                timeout=Timeout(10.0, connect=5.0),
            )

    async def _iter_all_requests(self):
        TOTAL_REQUESTS_NEEDED = 10_000 # all requests needed
        BATCH_SIZE = 250 # total Requests count per 1 time
        offset=0

        for _ in range(0, TOTAL_REQUESTS_NEEDED, BATCH_SIZE):
            input_data = {
            "operation": {
                "details": {
                    "limit": BATCH_SIZE,
                    "from": offset,
                    "filterby": "All_Requests",
                        }
                    }
                }
            params = {
                "OPERATION_NAME": "GET_REQUESTS",
                "TECHNICIAN_KEY": self._admin_api_key,
                "format": "json",
                "INPUT_DATA": self._encoder.encode(input_data).decode("utf-8"),
            }
            response = await self.client.get(url=self._endpoint, params=params)
            response.raise_for_status()
            parsed = self._decoder.decode(response.content)
            if parsed.operation.result and parsed.operation.result.status.lower() == "failed":
                raise HelpDeskAPIError(f"Ошибка HelpDesk API: {parsed.operation.result.message}")
            raw_details = parsed.operation.details
            if not raw_details:
                break
            batch = raw_details if isinstance(raw_details, list) else [raw_details]
            yield batch
            offset+=BATCH_SIZE


    async def get_request(self, request_id: int) -> RequestFullSchema:
        params = {
            "OPERATION_NAME": "GET_REQUEST",
            "TECHNICIAN_KEY": self._admin_api_key,
            "format": "json",
        }
        url = f"{self._endpoint}/{request_id}"

        response = await self.client.get(url=url, params=params)
        response.raise_for_status()
        raw_data = msgspec.json.decode(response.content)
        if "operation" in raw_data:
            result = raw_data["operation"].get("result", {})
            if result.get("status", "").lower() == "failed":
                raise HelpDeskAPIError(f"Ошибка API: {result.get('message')}")
            details = raw_data["operation"].get("details") or raw_data["operation"].get("Details") or {}
        else:
            details = raw_data
        if isinstance(details, list):
            details = details[0]
        if not details or "WORKORDERID" not in details:
            raise HelpDeskAPIError(f"Заявка #{request_id} не найдена или пуста")
        details["WORKORDERID"] = int(details["WORKORDERID"])
        return msgspec.convert(details, type=RequestFullSchema)

    
    async def get_requests(
        self,
        filter_by: str = "All_Pending",
        limit: int = 50,
        offset: int = 0,
        api_key: str | None = None,
    ) -> list[RequestSchema]:
        input_data = {
            "operation": {
                "details": {
                    "from": offset,
                    "limit": limit,
                    "filterby": filter_by
                }
            }
        }

        params = {
            "OPERATION_NAME": "GET_REQUESTS",
            "TECHNICIAN_KEY": api_key or self._admin_api_key,
            "format": "json",
            "INPUT_DATA": self._encoder.encode(input_data).decode("utf-8"),
            "requestViewChanged": "true",
            "viewName": filter_by, 
            "globalViewName": filter_by,
        }

        response = await self.client.get(url=self._endpoint, params=params)
        response.raise_for_status()
        parsed = self._decoder.decode(response.content)
        if parsed.operation.result and parsed.operation.result.status.lower() == "failed":
            raise HelpDeskAPIError(f"Ошибка HelpDesk API: {parsed.operation.result.message}")
        raw_details = parsed.operation.details
        if not raw_details:
            return []
        return raw_details if isinstance(raw_details, list) else [raw_details]

    async def get_technician_name(self, api_key: str) -> str | None:
        # Сначала ищем в открытых заявках юзера; если там пусто — проверяем все его заявки
        for filter_name in ("Open_User", "All_User"):
            requests = await self.get_requests(
                filter_by=filter_name,
                limit=1,
                api_key=api_key,
            )
            if requests and requests[0].technician:
                return requests[0].technician

        return None


    async def get_unassigned_requests(
    self,
    filter_by: str = "All_Requests",
    limit: int = 50,
    offset: int = 0,
    api_key: str | None = None,
    ) -> list[RequestSchema]:
        input_data = {
            "operation": {
                "details": {
                    "from": offset,
                    "limit": limit,
                    "filterby": filter_by,
                    "sortby": "lastupdatedtime",
                    "sortorder": "desc"
                }
            }
        }

        params = {
            "OPERATION_NAME": "GET_REQUESTS",
            "TECHNICIAN_KEY": api_key or self._admin_api_key,
            "format": "json",
            "INPUT_DATA": self._encoder.encode(input_data).decode("utf-8"),
        }

        response = await self.client.get(url=self._endpoint, params=params)
        response.raise_for_status()

        parsed = self._decoder.decode(response.content)

        if parsed.operation.result and parsed.operation.result.status.lower() == "failed":
            raise HelpDeskAPIError(f"Ошибка HelpDesk API: {parsed.operation.result.message}")

        raw_details = parsed.operation.details
        if not raw_details:
            return []

        return raw_details if isinstance(raw_details, list) else [raw_details]


    async def close(self) -> None:
        """Корректно закрывает пул соединений при остановке бота."""
        await self.client.aclose()


@lru_cache
def get_hd_client() -> HelpDeskClient:
    return HelpDeskClient()