from sqlalchemy.ext.asyncio import AsyncSession
from src.users.repository import UserRepository
from src.users.cached_repository import CachedUserRepository
from src.users.schemas import UserProfileCache

class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session=session)
        self.cached_repo = CachedUserRepository()

    async def warmup_cache_all_users(self):
        """Прогревает Redis актуальными настройками всех юзеров из Postgres."""
        db_users = await self.repo.get_active_users_with_settings()
        profiles_to_cache = []
        
        for user in db_users:
            active_preset = next((p for p in user.settings_presets if p.is_active), None)
            
            if not active_preset:
                continue

            profile = UserProfileCache(
                telegram_id=user.telegram_id,
                hd_api=user.hd_api,
                hd_technician_name=user.hd_technician_name,
                # Превращаем объект datetime.time в строку "HH:MM:SS" (если есть)
                time_from=active_preset.time_from.strftime("%H:%M:%S") if active_preset.time_from else None,
                time_to=active_preset.time_to.strftime("%H:%M:%S") if active_preset.time_to else None,
                days_of_week=active_preset.days_of_week,
                unassigned_requests=active_preset.unassigned_requests,
                assigned_to_me=active_preset.assigned_to_me,
                alerts=active_preset.alerts
            )
            profiles_to_cache.append(profile)

        # 3. Сохраняем в Redis
        if profiles_to_cache:
            await self.cached_repo.save_users(profiles_to_cache)
            print(f"Кэш юзеров обновлен: загружено {len(profiles_to_cache)} профилей.")