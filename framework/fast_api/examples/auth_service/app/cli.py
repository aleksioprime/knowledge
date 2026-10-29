"""Создать пользователя с ролью: python -m app.cli anna@example.com secret123 admin"""

import asyncio
import sys

from app.core.database import Base, SessionFactory, engine
from app.services.users import create_user, seed_roles


async def main(email: str, password: str, role: str) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_roles(session)
        user = await create_user(session, email, password, role)
        print(f'Создан пользователь {user.id} {user.email} с ролью {role}')
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main(*sys.argv[1:4]))
