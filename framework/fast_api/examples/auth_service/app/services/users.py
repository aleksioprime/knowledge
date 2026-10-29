from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import password_hash
from app.models import LoginHistory, Permission, Role, User

# роль → права; права пишем как «ресурс:действие»
ROLES = {
    'user': ['tasks:read', 'tasks:write'],
    'manager': ['tasks:read', 'tasks:write', 'tasks:delete'],
    'admin': ['tasks:read', 'tasks:write', 'tasks:delete', 'roles:manage'],
}
DEFAULT_ROLE = 'user'


async def seed_roles(session: AsyncSession) -> None:
    """Создать недостающие роли и права. Можно вызывать при каждом старте."""
    permissions = {p.code: p for p in await session.scalars(select(Permission))}
    roles = {r.name: r for r in await session.scalars(select(Role))}
    for role_name, codes in ROLES.items():
        role = roles.get(role_name) or Role(name=role_name)
        session.add(role)
        for code in codes:
            if code not in permissions:
                permissions[code] = Permission(code=code)
            if permissions[code] not in role.permissions:
                role.permissions.append(permissions[code])
    await session.commit()


async def get_role(session: AsyncSession, name: str) -> Role | None:
    return await session.scalar(select(Role).where(Role.name == name))


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def create_user(session: AsyncSession, email: str, password: str, role: str = DEFAULT_ROLE) -> User:
    user = User(email=email, password_hash=password_hash.hash(password), roles=[await get_role(session, role)])
    session.add(user)
    await session.commit()
    return user


async def authenticate(
    session: AsyncSession, email: str, password: str, user_agent: str, ip: str | None,
) -> User | None:
    user = await get_by_email(session, email)
    if user is None:
        return None
    ok = user.is_active and password_hash.verify(password, user.password_hash)
    session.add(LoginHistory(user_id=user.id, user_agent=user_agent, ip=ip, success=ok))
    await session.commit()
    return user if ok else None


async def login_history(session: AsyncSession, user_id: int, limit: int, offset: int) -> list[LoginHistory]:
    query = (
        select(LoginHistory)
        .where(LoginHistory.user_id == user_id)
        .order_by(LoginHistory.created_at.desc(), LoginHistory.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(query))
