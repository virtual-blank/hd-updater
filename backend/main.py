import asyncio
import time

from src.helpdesk.service import HelpDeskService
from core.logger import setup_logging



hd_service = HelpDeskService()
setup_logging()

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
