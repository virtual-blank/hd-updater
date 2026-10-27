import logging
import msgspec
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.repository import UserRepository
from src.users.cached_repository import CachedUserRepository
from src.users.schemas import UserProfileCache, UserCreateSchema, SettingsPresetUpdateSchema
from src.helpdesk.client import get_hd_client
from src.users.exceptions import TechnicianNameNotFound

log = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session=session)
        self.cached_repo = CachedUserRepository()
        self.hd_client = get_hd_client()

    async def warmup_cache_all_users(self) -> None:
        users_dao = await self.repo.get_active_users_with_settings()
        profiles_to_cache = []

        for user in users_dao:
            active_preset = next((p for p in user.settings_presets if p.is_active), None)
            if not active_preset:
                continue

            profile = UserProfileCache(
                telegram_id=user.telegram_id,
                hd_api=user.hd_api,
                hd_technician_name=user.hd_technician_name,
                time_from=active_preset.time_from.strftime("%H:%M:%S") if active_preset.time_from else None,
                time_to=active_preset.time_to.strftime("%H:%M:%S") if active_preset.time_to else None,
                days_of_week=active_preset.days_of_week,
                unassigned_requests=active_preset.unassigned_requests,
                assigned_to_me=active_preset.assigned_to_me,
                alerts=active_preset.alerts,
            )
            profiles_to_cache.append(profile)

        await self.cached_repo.save_users(profiles_to_cache)
        log.info(f"Users cache updated: loaded {len(profiles_to_cache)} profiles")

    async def create_user(self, user_data: UserCreateSchema):
        hd_technician_name = await self.hd_client.get_technician_name(api_key=user_data.hd_api)
        if not hd_technician_name:
            raise TechnicianNameNotFound("Could not find technician with provided heldpesk API-key")

        new_user = await self.repo.create_user(
            hd_api=user_data.hd_api, telegram_id=user_data.telegram_id, hd_technician_name=hd_technician_name
        )
        await self.repo._commit()

        await self.warmup_cache_all_users()
        return new_user

    async def edit_user_settings(self, telegram_id: int, settings_data: SettingsPresetUpdateSchema) -> None:
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram-id {telegram_id} not found")

        active_preset = next((p for p in user.settings_presets if p.is_active), None)
        if not active_preset:
            raise ValueError(f"User with telegram-id {telegram_id} has no settings presets")

        for field_name in settings_data.__struct_fields__:
            val = getattr(settings_data, field_name)
            if val is not msgspec.UNSET:
                setattr(active_preset, field_name, val)

        await self.repo._commit()
        await self.warmup_cache_all_users()
