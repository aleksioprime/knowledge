from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.exceptions import CodeGenerationError, LinkNotFoundError
from src.models import Link
from src.utils.shortener import generate_code

MAX_ATTEMPTS = 5


def link_key(code: str) -> str:
    return f'link:{code}'


def clicks_key(code: str) -> str:
    return f'clicks:{code}'


async def create_link(session: AsyncSession, url: str) -> Link:
    for _ in range(MAX_ATTEMPTS):
        link = Link(code=generate_code(), url=url)
        session.add(link)
        try:
            await session.commit()
        except IntegrityError:
            # Код уже занят: уникальный индекс не пустил дубль, пробуем другой
            await session.rollback()
            continue
        await session.refresh(link)
        return link
    raise CodeGenerationError


async def get_link(session: AsyncSession, code: str) -> Link:
    link = await session.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise LinkNotFoundError(code)
    return link


async def resolve(session: AsyncSession, cache: Redis, code: str) -> str:
    url = await cache.get(link_key(code))
    if url is None:
        url = (await get_link(session, code)).url
        await cache.set(link_key(code), url, ex=settings.cache_ttl_seconds)
    # Переходы считаем в Redis, а не UPDATE в базе: иначе популярная ссылка станет горячей строкой
    await cache.incr(clicks_key(code))
    return url


async def get_clicks(cache: Redis, code: str) -> int:
    return int(await cache.get(clicks_key(code)) or 0)
