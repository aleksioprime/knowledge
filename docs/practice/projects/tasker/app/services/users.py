from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas import UserCreate


class EmailTakenError(Exception):
    pass


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    if await session.scalar(select(User).where(User.email == data.email)):
        raise EmailTakenError(data.email)
    user = User(email=data.email, hashed_password=hash_password(data.password))
    session.add(user)
    await session.commit()
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
