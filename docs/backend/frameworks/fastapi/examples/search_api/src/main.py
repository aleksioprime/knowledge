from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1 import tasks
from src.core.config import settings
from src.db.elastic import create_elastic
from src.db.redis import create_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Клиенты создаются один раз на процесс: внутри у каждого пул соединений
    app.state.elastic = create_elastic()
    app.state.redis = create_redis()
    yield
    await app.state.elastic.close()
    await app.state.redis.aclose()


app = FastAPI(title=settings.project_name, lifespan=lifespan)
app.include_router(tasks.router)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
