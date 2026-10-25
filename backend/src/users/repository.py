from sqlalchemy.ext.asyncio import AsyncSession
from src.users.models import User
from sqlalchemy import select, update


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_hd_api(self, hd_api: str):
        stmt = select(User).where(User.hd_api == hd_api)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(self):
        stmt = select(User).where(User.hd_api != None)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_user(
        self,
        data_dict: dict
    ):
        stmt = update(User)

