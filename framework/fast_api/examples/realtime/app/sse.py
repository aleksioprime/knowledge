import asyncio
import json
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.auth import user_from_token
from app.bus import is_newer

router = APIRouter()


def query_user(request: Request, token: str = '') -> str:
    """EventSource не умеет ставить заголовки, поэтому токен приходит в адресе."""
    user_id = user_from_token(token, request.app.state.settings.jwt_secret)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'invalid token')
    return user_id


UserId = Annotated[str, Depends(query_user)]


def to_event(item: dict) -> ServerSentEvent:
    # raw_data: строку кладём как есть, без экранирования кириллицы в \uXXXX
    return ServerSentEvent(id=item['id'], event=item['event'], raw_data=json.dumps(item['data'], ensure_ascii=False))


@router.get('/events', response_class=EventSourceResponse)
async def notifications_sse(
    request: Request,
    user_id: UserId,
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    manager = request.app.state.manager
    bus = request.app.state.bus

    # Сначала подписываемся, потом читаем историю: так ничего не потеряется,
    # а повторы отсечёт проверка is_newer.
    queue = manager.listen(user_id)
    try:
        yield ServerSentEvent(comment='connected', retry=3000)
        sent = last_event_id
        if last_event_id:
            for item in await bus.missed(user_id, last_event_id):
                yield to_event(item)
                sent = item['id']
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=5)
            except TimeoutError:
                if await request.is_disconnected():
                    break
                continue
            if item is None:
                break
            if is_newer(item['id'], sent):
                yield to_event(item)
                sent = item['id']
    finally:
        manager.unlisten(user_id, queue)


@router.get('/poll')
async def long_poll(
    request: Request,
    user_id: UserId,
    after: str | None = None,
    timeout: Annotated[float, Query(gt=0, le=55)] = 25,
) -> dict:
    """Long polling: ответ приходит, как только есть событие, или пустой по таймауту."""
    manager = request.app.state.manager
    queue = manager.listen(user_id)
    try:
        if after:
            if missed := await request.app.state.bus.missed(user_id, after):
                return {'items': missed}
        try:
            item = await asyncio.wait_for(queue.get(), timeout)
        except TimeoutError:
            return {'items': []}
        return {'items': [item] if item else []}
    finally:
        manager.unlisten(user_id, queue)
