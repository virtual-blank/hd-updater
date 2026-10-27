from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from src.users.models import User, SettingsPreset
from src.users.exceptions import TelegramAlreadyUsed, HdApiAlreadyUsed
from src.users.schemas import SettingsPresetUpdateSchema


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _commit(self):
        await self.session.commit()

    async def _rollback(self):
        await self.session.rollback()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.settings_presets))
            .where(User.telegram_id == telegram_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_hd_api(self, hd_api: str) -> User | None:
        stmt = select(User).where(User.hd_api == hd_api)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        hd_api: str,
        telegram_id: int,
        hd_technician_name: str 
    ) -> User:
        new_user = User(
            telegram_id=telegram_id,
            hd_api=hd_api,
            hd_technician_name=hd_technician_name,
            settings_presets=[
                SettingsPreset(name="Стандартный", is_active=True)
            ]
        )
        try:
            self.session.add(new_user)
            await self.session.flush() 
        except IntegrityError as exc:
            await self._rollback()     
            err_msg = str(exc.orig)
            if "telegram_id" in err_msg:
                raise TelegramAlreadyUsed from exc
            if "hd_api" in err_msg:
                raise HdApiAlreadyUsed from exc
            raise
        except Exception:
            await self._rollback()
            raise                      

        return new_user

    async def get_active_users_with_settings(self) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.settings_presets))
            .where(User.hd_api.is_not(None))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())