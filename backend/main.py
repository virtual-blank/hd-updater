import asyncio
import time

from src.helpdesk.service import HelpDeskService


hd_service = HelpDeskService()

async def main():
    await hd_service.fill_cache()
    
    while True:
        print("Ждем 10 сек...")
        await asyncio.sleep(10)
        events = await hd_service.process_requests()
        

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
