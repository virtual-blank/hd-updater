import asyncio
from httpx import AsyncClient

async def get_my_filters():
    url = "https://ihelpdesk.me/sdpapi/request"
    params = {
        "OPERATION_NAME": "GET_REQUEST_FILTERS",
        "TECHNICIAN_KEY": "6CCD91E0-1792-456A-B77E-808824317D08",
        "format": "json"
    }
    
    async with AsyncClient(verify=False) as client:
        resp = await client.get(url, params=params)
        print(resp.text)

asyncio.run(get_my_filters())