import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.auth import user_from_token
from app.config import Settings
from app.limits import TokenBucket

router = APIRouter()


async def authenticate(websocket: WebSocket, token: str | None, settings: Settings) -> str | None:
    """Токен из адреса или из первого сообщения {"type": "auth", "token": "..."}."""
    if token is None:
        try:
            first = await asyncio.wait_for(websocket.receive_json(), settings.auth_timeout)
        except (TimeoutError, ValueError, KeyError):
            return None
        if not isinstance(first, dict) or first.get('type') != 'auth':
            return None
        token = first.get('token')
    return user_from_token(token, settings.jwt_secret)


async def handle(websocket: WebSocket, text: str) -> None:
    try:
        message = json.loads(text)
    except ValueError:
        await websocket.send_json({'type': 'error', 'detail': 'ожидается JSON'})
        return
    match message:
        case {'type': 'ping'}:
            await websocket.send_json({'type': 'pong'})
        case {'type': 'read', 'id': str(event_id)}:
            await websocket.send_json({'type': 'ack', 'id': event_id})
        case _:
            await websocket.send_json({'type': 'error', 'detail': 'неизвестное сообщение'})


@router.websocket('/ws')
async def notifications_ws(websocket: WebSocket, token: str | None = None, last_id: str | None = None):
    settings: Settings = websocket.app.state.settings
    manager = websocket.app.state.manager
    bus = websocket.app.state.bus

    origin = websocket.headers.get('origin')
    if origin is not None and origin not in settings.allowed_origins:
        # Закрытие до accept: клиент получит отказ рукопожатия (HTTP 403)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        user_id = await authenticate(websocket, token, settings)
    except WebSocketDisconnect:
        return
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='invalid token')
        return

    manager.add(user_id, websocket)
    limiter = TokenBucket(settings.messages_per_second, settings.messages_burst)
    try:
        await websocket.send_json({'type': 'hello', 'user_id': user_id, 'instance': settings.instance})
        if last_id:
            for item in await bus.missed(user_id, last_id):
                await websocket.send_json({'type': 'notification', **item})
        while True:
            text = await websocket.receive_text()
            if len(text.encode()) > settings.max_message_bytes:
                await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG, reason='message too big')
                break
            if not limiter.allow():
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='too many messages')
                break
            await handle(websocket, text)
    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(user_id, websocket)
