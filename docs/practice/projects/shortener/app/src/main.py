from typing import Annotated

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src import service
from src.config import settings
from src.database.cache import get_cache
from src.database.db import get_session
from src.exceptions import CodeGenerationError, LinkNotFoundError
from src.schemas import LinkCreate, LinkRead, LinkStats

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CacheDep = Annotated[Redis, Depends(get_cache)]

app = FastAPI(title='Сокращатель ссылок')


@app.exception_handler(LinkNotFoundError)
async def link_not_found(request: Request, exc: LinkNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={'detail': 'Ссылка не найдена'})


@app.exception_handler(CodeGenerationError)
async def code_generation_failed(request: Request, exc: CodeGenerationError) -> JSONResponse:
    return JSONResponse(status_code=503, content={'detail': 'Не удалось подобрать свободный код, повторите запрос'})


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/api/links', status_code=status.HTTP_201_CREATED)
async def create_link(data: LinkCreate, session: SessionDep) -> LinkRead:
    link = await service.create_link(session, str(data.url))
    return LinkRead(code=link.code, short_url=f'{settings.base_url}/{link.code}')


@app.get('/api/links/{code}/stats')
async def link_stats(code: str, session: SessionDep, cache: CacheDep) -> LinkStats:
    link = await service.get_link(session, code)
    clicks = await service.get_clicks(cache, code)
    return LinkStats(code=link.code, url=link.url, clicks=clicks, created_at=link.created_at)


# Маршрут с переменной в корне объявлен последним, чтобы не перехватывать /health и /docs
@app.get('/{code}', status_code=status.HTTP_302_FOUND)
async def redirect(code: str, session: SessionDep, cache: CacheDep) -> RedirectResponse:
    url = await service.resolve(session, cache, code)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)
