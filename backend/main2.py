import asyncio
from src.helpdesk.service import HelpDeskService
from src.users.cached_repository import CachedUserRepository
from src.users.schemas import UserProfileCache
from core.logger import setup_logging

setup_logging()

async def main():
    hd_service = HelpDeskService()
    user_cache = CachedUserRepository()

    # test usr for redis
    await user_cache.save_users([
        UserProfileCache(
            telegram_id=123456789,
            hd_api="test_key",
            hd_technician_name="Даниил Федотов",
            time_from="08:00:00",
            time_to="23:00:00",
            days_of_week=[0, 1, 2, 3, 4, 5, 6],
            unassigned_requests=True,
            assigned_to_me=True,
            alerts=True,
        )
    ])

    await hd_service.fill_cache()

    while True:
        await asyncio.sleep(10)
        notifications = await hd_service.process_requests()
        for item in notifications:
            print(
                f"🚀 ОТПРАВКА В TG ({item.telegram_id}) | Событие: {item.event_type}\n"
                f"Заявка #{item.request.id}: {item.request.subject}\n"
                f"Исполнитель: {item.request.technician}\n"
                f"Описание: {item.request.description}\n"
            )

if __name__ == "__main__":
    asyncio.run(main())