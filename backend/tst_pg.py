from httpx import AsyncClient, HTTPError
from core.config import get_hd_settings
from datetime import datetime, timezone, timedelta
import asyncio
import json
import msgspec
from typing import Any


HD_API_KEY = get_hd_settings().api_key

API_KEY = HD_API_KEY
BASE_URL = "https://ihelpdesk.me"

endpoint = f"{BASE_URL}/sdpapi/request"

input_data_dict = {
    "operation": {
        "details": {
            "from": 0,
            "limit": 10,
            "filterby": "All_Requests" 
        }
    }
}

params = {
    "OPERATION_NAME": "GET_REQUESTS",
    "TECHNICIAN_KEY": API_KEY,
    "format": "json",
    "INPUT_DATA": json.dumps(input_data_dict)
}

headers = {}


def get_client() -> AsyncClient:
    return AsyncClient(verify=False, http2=True)




class Request(msgspec.Struct):
    id: int = msgspec.field(name="WORKORDERID")
    subject: str = msgspec.field(name="SUBJECT", default="Без темы")
    status: str = msgspec.field(name="STATUS", default="-")

class OperationDetails(msgspec.Struct):
    details: list[Request] | Request | None = None

class SdpResponse(msgspec.Struct):
    operation: OperationDetails


async def get_my_operations(client: AsyncClient):
    try:
        response = await client.get(url=endpoint, headers=headers, params=params) 
        response.raise_for_status()
        print(f"HTTP Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Ошибка соединения: {response.status_code}")
            return 
        parsed_response = msgspec.json.decode(response.content, type=SdpResponse)
        raw_details = parsed_response.operation.details 
        if not raw_details:
            return None
        else:
            requests_list = raw_details if isinstance(raw_details, list) else [raw_details]
        for request in requests_list:
            if request.status.lower() != "в работе":
                continue
            print(f"Заявка: {request.id} | Описание: {request.subject} | Статус: {request.status}")



    except HTTPError as exc:
        print(f"Connection error: {str(exc)}")
    except Exception as exc:
        print(f"Error: {str(exc)}")

async def get_unassigned_requests(client: AsyncClient):
    input_data_dict = {
    "operation": {
        "details": {
            "from": 0,
            "limit": 100,  # Ограничение на количество запрашиваемых заявок
            "filterby": "Unassigned_System" # <-- Тот самый ID
                }
            }
        }

    params = {
        "OPERATION_NAME": "GET_REQUESTS",
        "TECHNICIAN_KEY": HD_API_KEY,
        "format": "json",
        "INPUT_DATA": json.dumps(input_data_dict)
        }

    try:
        response = await client.get(url=endpoint, params=params)
        response.raise_for_status()
        
        data = response.json()
        details = data.get("operation", {}).get("details", [])
        

        requests_list = details if isinstance(details, list) else [details] if details else []
        
        print(f"Найдено неназначенных заявок: {len(requests_list)}")
        
        for req in requests_list:
            req_id = req.get("WORKORDERID")
            subject = req.get("SUBJECT")
            status = req.get("STATUS")
            print(f"ID: {req_id} | Статус: {status} | Тема: {subject}")
            
        return requests_list

    except HTTPError as exc:
        print(f"Connection error: {str(exc)}")
    except Exception as exc:
        print(f"Error: {str(exc)}")


async def catch_unassigned_loop(client: AsyncClient):
    EXP_MINUTES = 60 # 1h 
    for _ in range(1, EXP_MINUTES):
        unassigned_requests = await get_unassigned_requests(client=client)
        if not unassigned_requests:
            pass
            # тут еще добавить чтобы id заявки сохранялось, чтобы не дублировать уже полученную заявку



async def get_me(client: AsyncClient):
    api_key = API_KEY
    endpoint = "https://ihelpdesk.me/sdpapi/request"
    
    # Запрашиваем всего 1 заявку из личного фильтра инженера
    input_data = {
        "operation": {
            "details": {
                "from": 0,
                "limit": 1,
                "filterby": "Open_User" 
            }
        }
    }
    
    params = {
        "OPERATION_NAME": "GET_REQUESTS",
        "TECHNICIAN_KEY": api_key,
        "format": "json",
        "INPUT_DATA": json.dumps(input_data)
    }
    
    try:
        response = await client.get(url=endpoint, params=params)
        response.raise_for_status()
        
        data = response.json()
        details = data.get("operation", {}).get("details", [])
        
        requests_list = details if isinstance(details, list) else [details] if details else []
        
        if not requests_list:
            print("У этого ключа сейчас нет открытых заявок. Невозможно извлечь имя.")
            return None
            
        # Берем первую личную заявку и достаем поле инженера
        first_req = requests_list[0]
        technician_name = first_req.get("TECHNICIAN")
        
        print(f"Успешно вытащили имя по ключу: {technician_name}")
        return {
            "api_key": api_key,
            "name": technician_name
        }
        
    except HTTPError as exc:
        print(f"Ошибка HTTP: {str(exc)}")
    except Exception as exc:
        print(f"Ошибка: {str(exc)}")
        
    return None

async def main():
    #now = datetime.now()
    #current_time = now.strftime("%H:%M:%S")
    #print("Текущее время:", current_time)
    #print(f"{current_time=}")
    client = get_client()
    res = await get_my_operations(client=client)
    print(res)
    #res_2 = await get_unassigned_requests(client=client)
    #print(res_2)
    #me = await get_me(client=client)
    #print(f"{me=}")
    return
    



if __name__ == "__main__":
    asyncio.run(main())
