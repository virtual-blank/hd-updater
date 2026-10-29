import asyncio
import json
from httpx import AsyncClient
from core.config import get_hd_settings

async def test_v3_history():
    settings = get_hd_settings()
    api_key = settings.admin_api_key 
    url = f"{settings.base_url.rstrip('/')}/api/v3/requests/34754/history"
    input_data = json.dumps({"list_info": {"sort_order": "A"}})

    variants = [
        #  TECHNICIAN_KEY, гибридные V1/V3 билды
        {
            "name": "Query param TECHNICIAN_KEY",
            "headers": {"Accept": "application/vnd.manageengine.sdp.v3+json"},
            "params": {"TECHNICIAN_KEY": api_key, "INPUT_DATA": input_data},
        },
        # хедер authtoken, стандарт старых V3
        {
            "name": "Header authtoken",
            "headers": {"authtoken": api_key, "Accept": "application/vnd.manageengine.sdp.v3+json"},
            "params": {"INPUT_DATA": input_data},
        },
        # хедер TECHNICIAN_KEY + query format=json
        {
            "name": "Header + Query combined",
            "headers": {"TECHNICIAN_KEY": api_key, "authtoken": api_key, "X-Requested-With": "XMLHttpRequest"},
            "params": {"TECHNICIAN_KEY": api_key, "format": "json", "INPUT_DATA": input_data},
        },
    ]

    async with AsyncClient(verify=False, http2=True) as client:
        for v in variants:
            print(f"\n=== трай: {v['name']} ===")
            resp = await client.get(url, headers=v["headers"], params=v["params"])
            data = resp.json()
            if "history" in data:
                print("✅ УСПЕХ! Элемент history[3]:")
                print(json.dumps(data["history"][3], indent=2, ensure_ascii=False))
                break
            else:
                print("❌ Отказ:", resp.text[:300])

asyncio.run(test_v3_history())

