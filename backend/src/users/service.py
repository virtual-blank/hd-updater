import logging
import uuid
import msgspec
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.models import User, SettingsPreset
from src.users.repository import UserRepository
from src.users.cached_repository import CachedUserRepository
from src.users.schemas import (
    UserProfileCache,
    UserCreateSchema,
    UserOutputSchema,
    UserSettingsOutputSchema,
    SettingsPresetCreateSchema,
    SettingsPresetUpdateSchema,
)
from src.helpdesk.client import get_hd_client
from src.users.exceptions import (
    TechnicianNameNotFound,
    UserNotFound,
    PresetNotFound,
    PresetLimitExceeded,
    CannotDeleteLastPreset,
)

log = logging.getLogger(__name__)

MAX_PRESETS_PER_USER = 5


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session=session)
        self.cached_repo = CachedUserRepository()
        self.hd_client = get_hd_client()

    # --- Вспомогательные мапперы в DTO ---

    @staticmethod
    def _map_preset_to_schema(preset: SettingsPreset) -> UserSettingsOutputSchema:
        return UserSettingsOutputSchema(
            id=preset.id,
            name=preset.name,
            is_active=preset.is_active,
            time_from=preset.time_from.strftime("%H:%M:%S") if preset.time_from else None,
            time_to=preset.time_to.strftime("%H:%M:%S") if preset.time_to else None,
            days_of_week=list(preset.days_of_week),
            unassigned_requests=preset.unassigned_requests,
            assigned_to_me=preset.assigned_to_me,
            alerts=preset.alerts,
        )

    def _map_user_to_schema(self, user: User) -> UserOutputSchema:
        return UserOutputSchema(
            id=user.id,
            telegram_id=user.telegram_id,
            hd_api=user.hd_api,
            hd_technician_name=user.hd_technician_name,
            settings=[self._map_preset_to_schema(p) for p in user.settings_presets],
        )

    # --- Кэширование ---

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
                days_of_week=list(active_preset.days_of_week),
                unassigned_requests=active_preset.unassigned_requests,
                assigned_to_me=active_preset.assigned_to_me,
                alerts=active_preset.alerts,
            )
            profiles_to_cache.append(profile)

        await self.cached_repo.save_users(profiles_to_cache)
        log.info(f"Users cache updated: loaded {len(profiles_to_cache)} profiles")

    # --- Работа с пользователем ---

    async def get_user_profile(self, telegram_id: int) -> UserOutputSchema:
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")
        return self._map_user_to_schema(user)

    async def create_user(self, user_data: UserCreateSchema) -> UserOutputSchema:
        hd_technician_name = await self.hd_client.get_technician_name(api_key=user_data.hd_api)
        if not hd_technician_name:
            raise TechnicianNameNotFound("Could not find technician with provided helpdesk API-key")

        new_user = await self.repo.create_user(
            hd_api=user_data.hd_api,
            telegram_id=user_data.telegram_id,
            hd_technician_name=hd_technician_name,
        )
        await self.repo._commit()
        await self.warmup_cache_all_users()

        return self._map_user_to_schema(new_user)

    async def update_hd_api_key(self, telegram_id: int, new_hd_api: str) -> UserOutputSchema:
        """Позволяет юзеру сменить API-ключ, если старый протух или перевыпущен."""
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")

        hd_technician_name = await self.hd_client.get_technician_name(api_key=new_hd_api)
        if not hd_technician_name:
            raise TechnicianNameNotFound("Could not find technician with provided helpdesk API-key")

        user.hd_api = new_hd_api
        user.hd_technician_name = hd_technician_name

        await self.repo._commit()
        await self.warmup_cache_all_users()
        return self._map_user_to_schema(user)

    # --- Управление пресетами уведомлений ---

    def _get_target_preset(
        self, user: User, preset_id: uuid.UUID | None = None
    ) -> SettingsPreset:
        if preset_id is not None:
            preset = next((p for p in user.settings_presets if p.id == preset_id), None)
        else:
            preset = next((p for p in user.settings_presets if p.is_active), None)

        if not preset:
            raise PresetNotFound("Target settings preset not found")
        return preset

    async def create_preset(
        self, telegram_id: int, data: SettingsPresetCreateSchema
    ) -> UserSettingsOutputSchema:
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")

        if len(user.settings_presets) >= MAX_PRESETS_PER_USER:
            raise PresetLimitExceeded(f"Maximum {MAX_PRESETS_PER_USER} presets allowed")

        if data.activate_immediately:
            for p in user.settings_presets:
                p.is_active = False

        new_preset = SettingsPreset(
            user_id=user.id,
            name=data.name,
            is_active=data.activate_immediately or len(user.settings_presets) == 0,
            time_from=data.time_from,
            time_to=data.time_to,
            days_of_week=sorted(set(data.days_of_week)),
            unassigned_requests=data.unassigned_requests,
            assigned_to_me=data.assigned_to_me,
            alerts=data.alerts,
        )
        await self.repo.add_preset(new_preset)
        await self.repo._commit()
        await self.warmup_cache_all_users()

        return self._map_preset_to_schema(new_preset)

    async def activate_preset(
        self, telegram_id: int, preset_id: uuid.UUID
    ) -> UserSettingsOutputSchema:
        """Переключает активный профиль уведомлений на выбранный."""
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")

        target = self._get_target_preset(user, preset_id)

        for p in user.settings_presets:
            p.is_active = (p.id == target.id)

        await self.repo._commit()
        await self.warmup_cache_all_users()
        return self._map_preset_to_schema(target)

    async def edit_user_settings(
        self,
        telegram_id: int,
        settings_data: SettingsPresetUpdateSchema,
        preset_id: uuid.UUID | None = None,
    ) -> UserSettingsOutputSchema:
        """
        Обновляет настройки конкретного пресета (если передан preset_id)
        или текущего активного пресета (если preset_id=None).
        """
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")

        preset = self._get_target_preset(user, preset_id)

        for field_name in settings_data.__struct_fields__:
            val = getattr(settings_data, field_name)
            if val is not msgspec.UNSET:
                if field_name == "days_of_week" and val is not None:
                    # Присваиваем новый отсортированный список, чтобы SQLAlchemy заметила diff в ARRAY
                    setattr(preset, field_name, sorted(set(val)))
                else:
                    setattr(preset, field_name, val)

        await self.repo._commit()
        await self.warmup_cache_all_users()
        return self._map_preset_to_schema(preset)

    async def toggle_preset_day(
        self,
        telegram_id: int,
        day: int,
        preset_id: uuid.UUID | None = None,
    ) -> UserSettingsOutputSchema:
        """
        Удобный хелпер для инлайн-кнопок дней недели (0=Пн .. 6=Вс).
        Если день включен — выключает, если выключен — включает.
        """
        if day not in range(7):
            raise ValueError("Day must be between 0 (Monday) and 6 (Sunday)")

        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")

        preset = self._get_target_preset(user, preset_id)
        current_days = set(preset.days_of_week or [])

        if day in current_days:
            current_days.remove(day)
        else:
            current_days.add(day)

        # Обязательно создаем новый объект list для колонки PostgreSQL ARRAY
        preset.days_of_week = sorted(current_days)

        await self.repo._commit()
        await self.warmup_cache_all_users()
        return self._map_preset_to_schema(preset)

    async def delete_preset(
        self, telegram_id: int, preset_id: uuid.UUID
    ) -> UserOutputSchema:
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFound(f"User with telegram_id {telegram_id} not found")

        if len(user.settings_presets) <= 1:
            raise CannotDeleteLastPreset("Cannot delete the only remaining settings preset")

        target = self._get_target_preset(user, preset_id)
        was_active = target.is_active

        user.settings_presets.remove(target)
        await self.repo.delete_preset(target)

        # Если удалили активный пресет — автоматически делаем активным первый оставшийся
        if was_active and user.settings_presets:
            user.settings_presets[0].is_active = True

        await self.repo._commit()
        await self.warmup_cache_all_users()
        return self._map_user_to_schema(user)