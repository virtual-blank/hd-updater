import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import get_hd_settings
from src.helpdesk.service import HelpDeskService
from src.telegram.bot import dispatch_helpdesk_events

log = logging.getLogger(__name__)

settings = get_hd_settings()
ACTIVE_HOURS_START = datetime.strptime(settings.active_hours_start, "%H:%M").time()
ACTIVE_HOURS_END = datetime.strptime(settings.active_hours_end, "%H:%M").time()

WINDOW_ACTIVE_SECONDS = settings.active_hours_polling_period_seconds
WINDOW_INACTIVE_SECONDS = settings.inactive_hours_polling_period_seconds
TZ = settings.tzinfo

JOB_ID = "poll_helpdesk_requests"

scheduler = AsyncIOScheduler(timezone=TZ)
hd_service = HelpDeskService()

_current_interval: int = WINDOW_ACTIVE_SECONDS


def _get_target_interval() -> int:
    now_time = datetime.now(TZ).time()
    if ACTIVE_HOURS_START <= ACTIVE_HOURS_END:
        is_active = ACTIVE_HOURS_START <= now_time <= ACTIVE_HOURS_END
    else:
        is_active = now_time >= ACTIVE_HOURS_START or now_time <= ACTIVE_HOURS_END
    return WINDOW_ACTIVE_SECONDS if is_active else WINDOW_INACTIVE_SECONDS


async def _poll_helpdesk_job() -> None:
    global _current_interval

    notifications, assigned_requests = await hd_service.process_requests()
    if notifications or assigned_requests:
        await dispatch_helpdesk_events(notifications, assigned_requests)

    target_interval = _get_target_interval()
    if target_interval != _current_interval:
        _current_interval = target_interval
        scheduler.reschedule_job(
            JOB_ID, trigger="interval", seconds=_current_interval
        )
        log.info(f"HelpDesk polling interval changed to {_current_interval} sec.")


def start_scheduler() -> None:
    global _current_interval
    if not scheduler.running:
        _current_interval = _get_target_interval()
        scheduler.add_job(
            _poll_helpdesk_job,
            trigger="interval",
            seconds=_current_interval,
            id=JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        log.info(f"HelpDesk scheduler started. Interval= {_current_interval} sec.")