from sqlalchemy.ext.asyncio import AsyncSession
from src.users.repository import UserRepository
from src.users.cached_repository import CachedUserRepository

class UserService:
    def __init__(self, session: AsyncSession):
        self.repo=UserRepository(session=session)
        self.cached_repo=CachedUserRepository

    
        