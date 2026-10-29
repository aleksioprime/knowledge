from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import auth, tasks, users
from app.core.database import Base, SessionFactory, engine
from app.core.redis import redis_client
from app.services.users import seed_roles


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Учебное упрощение: таблицы создаются при старте. В рабочем проекте — миграции Alembic.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_roles(session)
    yield
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(title='Auth-сервис Задачника', lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
