from sqlalchemy.ext.asyncio import AsyncSession
from src.users.models import User
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _commit(self):
        await self.session.commit()

    async def _rollback(self):
        await self.session.rollback()

    async def get_user_by_hd_api(self, hd_api: str):
        stmt = select(User).where(User.hd_api == hd_api)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_name(self, name: str):
        stmt = select(User).where(User.hd_technician_name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def create_user(
        self,
        hd_api: str,
        telegram_id: int,
        hd_technician_name: str 
    ):
        new_user = User(
            telegram_id=telegram_id,
            hd_api=hd_api,
            hd_technician_name=hd_technician_name
        )
        self.session.add(new_user)
        

    async def get_active_users_with_settings(self):
        stmt = (
            select(User)
            .options(
                selectinload(User.settings_presets)
            )
            .where(User.hd_api.is_not(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()




