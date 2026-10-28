import logging
from datetime import datetime, time

from src.helpdesk.cached_repository import CachedHelpdeskRepository
from src.helpdesk.client import get_hd_client
from src.helpdesk.schemas import (
    NotificationEventSchema,
    RequestFullSchema,
    RequestSchema,
)
from src.users.cached_repository import CachedUserRepository
from src.users.schemas import UserProfileCache

log = logging.getLogger(__name__)


class HelpDeskService:
    def __init__(self):
        self.hd_client = get_hd_client()
        self.cached_repo = CachedHelpdeskRepository()
        self.cached_user_repo = CachedUserRepository()

    async def fill_cache(self):
        return await self.cached_repo.warmup_cache_all_requests()

    async def check_new_requests(self) -> list[tuple[str, RequestSchema]]:
        current_requests = await self.hd_client.get_requests()
        known_requests = await self.cached_repo.get_known_requests()
        events: list[tuple[str, RequestSchema]] = []
        for req in current_requests:
            if req.id not in known_requests:
                if not req.technician:
                    events.append(("NEW_UNASSIGNED", req))
                else:
                    events.append(("ASSIGNED", req))
            else:
                old_tech = known_requests[req.id]
                if req.technician and req.technician != old_tech:
                    events.append(("ASSIGNED", req))
        if current_requests:
            await self.cached_repo.update_known_requests(current_requests)
        return events

    def _is_within_schedule(self, user: UserProfileCache, now: datetime) -> bool:
        if now.weekday() not in user.days_of_week:
            return False
        if not user.time_from or not user.time_to:
            return True
        t_from = time.fromisoformat(user.time_from)
        t_to = time.fromisoformat(user.time_to)
        current_time = now.time()
        if t_from <= t_to:
            return t_from <= current_time <= t_to
        else:
            return current_time >= t_from or current_time <= t_to

    def _should_notify(
        self,
        user: UserProfileCache,
        event_type: str,
        req: RequestFullSchema,
        now: datetime,
    ) -> bool:
        if not user.alerts:
            return False

        if not self._is_within_schedule(user, now):
            return False

        if event_type == "NEW_UNASSIGNED":
            return user.unassigned_requests

        if event_type == "ASSIGNED":
            if not user.assigned_to_me:
                return False
            return user.hd_technician_name.strip().lower() == req.technician.strip().lower()

        return False

    # async def process_requests(self) -> list[NotificationEventSchema]:
    #     events = await self.check_new_requests()
    #     if not events:
    #         log.debug("No changes found")
    #         return []
    #     log.info(f"Found {len(events)} new events in helpdesk")
    #     active_users = await self.cached_user_repo.get_users()
    #     if not active_users:
    #         log.warning("Got events but cache is empty")
    #         return []
    #     now = datetime.now()
    #     notifications: list[NotificationEventSchema] = []
    #     for event_type, short_req in events:
    #         try:
    #             full_request = await self.hd_client.get_request(request_id=short_req.id)
    #         except Exception as exc:
    #             log.error(f"Could not get details for request #{short_req.id}: {exc}")
    #             continue
    #         for user in active_users:
    #             if self._should_notify(user, event_type, full_request, now):
    #                 notifications.append(
    #                     NotificationEventSchema(
    #                         telegram_id=user.telegram_id,
    #                         event_type=event_type,
    #                         request=full_request,
    #                     )
    #                 )
    #                 log.info(
    #                     f"Created notification [{event_type}] with request #{full_request.id} "
    #                     f"for {user.hd_technician_name} (TG: {user.telegram_id})"
    #                 )

    #     return notifications


    async def process_requests(self) -> list[NotificationEventSchema]:
        events = await self.check_new_requests()
        if not events:
            log.debug("No changes found")
            return []

        log.info(f"Found {len(events)} new events in helpdesk")

        active_users = await self.cached_user_repo.get_users()
        if not active_users:
            log.warning("Events found, but users cache in Redis is empty!")
            return []

        now = datetime.now()
        notifications: list[NotificationEventSchema] = []

        for event_type, short_req in events:
            try:
                full_request = await self.hd_client.get_request(request_id=short_req.id)
            except Exception as exc:
                log.error(f"Failed to fetch details for request #{short_req.id}: {exc}")
                continue

            # Если заявку назначили — проверяем по истории, не сам ли на себя повесил специалист
            if event_type == "ASSIGNED" and full_request.technician:
                try:
                    editor_name = await self.hd_client.get_last_assignee_editor(short_req.id)
                except Exception as exc:
                    log.warning(f"Failed to fetch history for request #{short_req.id}: {exc}")
                    editor_name = None

                if (
                    editor_name
                    and editor_name.strip().lower() == full_request.technician.strip().lower()
                ):
                    log.info(
                        f"Request #{short_req.id}: self-assigned by {editor_name}. "
                        f"Notification skipped."
                    )
                    continue

            # Проверяем, кому из активных пользователей подходит это уведомление
            for user in active_users:
                if self._should_notify(user, event_type, full_request, now):
                    notifications.append(
                        NotificationEventSchema(
                            telegram_id=user.telegram_id,
                            event_type=event_type,
                            request=full_request,
                        )
                    )
                    log.info(
                        f"Created notification [{event_type}] with request #{full_request.id} "
                        f"for {user.hd_technician_name} (TG: {user.telegram_id})"
                    )

        return notifications
