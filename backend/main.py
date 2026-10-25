import asyncio

from src.helpdesk.client import get_hd_client


hd_client = get_hd_client()

async def main():
    res = await hd_client.get_requests(api_key="6CCD91E0-1792-456A-B77E-808824317D08")
    print(res)
    return 
    

if __name__ == "__main__":
    asyncio.run(main())