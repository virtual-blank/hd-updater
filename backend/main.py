import asyncio
import logging

from core.logger import setup_logging
from database.db import async_session_factory
from src.helpdesk.client import get_hd_client
from src.helpdesk.service import HelpDeskService
from src.scheduler.scheduler import scheduler, start_scheduler
from src.telegram.bot import bot, dp
from src.users.service import UserService

setup_logging()
log = logging.getLogger(__name__)

# todo: настроить alembic, поднимать миграции каждый раз при запуске постгрес



async def main() -> None:
    log.info("Прогрев кэша пользователей из БД...")
    async with async_session_factory() as session:
        user_service = UserService(session)
        await user_service.warmup_cache_all_users()

    log.info("Прогрев кэша заявок из HelpDesk...")
    hd_service = HelpDeskService()
    await hd_service.fill_cache()

    start_scheduler()

    log.info("Запуск Telegram-бота...")
    try:
        await dp.start_polling(bot)
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await get_hd_client().close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())