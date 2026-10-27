import asyncio
from httpx import AsyncClient

async def test_history():
    url = "https://ihelpdesk.me/sdpapi/request/34706"
    
    for op_name in ("GET_HISTORY", "GET_REQUEST_HISTORY", "GET_CONVERSATIONS", "GET_WORKLOGS"):
        params = {
            "OPERATION_NAME": op_name,
            "TECHNICIAN_KEY": "6CCD91E0-1792-456A-B77E-808824317D08",
            "format": "json"
        }
        async with AsyncClient(verify=False) as client:
            resp = await client.get(url, params=params)
            print(f"=== Операция: {op_name} ===")
            print(resp.text[:500]) 

asyncio.run(test_history())