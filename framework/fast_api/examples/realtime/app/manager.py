import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Кто подключён к этому экземпляру сервиса.

    У одного пользователя может быть несколько вкладок, поэтому на каждого
    хранится набор соединений. SSE и long polling получают события через очередь.
    """

    def __init__(self, send_timeout: float = 2.0, queue_size: int = 100):
        self.send_timeout = send_timeout
        self.queue_size = queue_size
        self.sockets: dict[str, set[WebSocket]] = defaultdict(set)
        self.queues: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def add(self, user_id: str, websocket: WebSocket) -> None:
        self.sockets[user_id].add(websocket)

    def remove(self, user_id: str, websocket: WebSocket) -> None:
        connections = self.sockets.get(user_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            del self.sockets[user_id]

    def listen(self, user_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_size)
        self.queues[user_id].add(queue)
        return queue

    def unlisten(self, user_id: str, queue: asyncio.Queue) -> None:
        queues = self.queues.get(user_id)
        if queues is None:
            return
        queues.discard(queue)
        if not queues:
            del self.queues[user_id]

    def stats(self) -> dict:
        return {
            'websocket': {user: len(conns) for user, conns in self.sockets.items()},
            'sse': {user: len(queues) for user, queues in self.queues.items()},
        }

    async def deliver(self, user_id: str, message: dict) -> None:
        for queue in list(self.queues.get(user_id, ())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Клиент не успевает читать: закрываем поток, он переподключится
                # и догрузит пропущенное по Last-Event-ID.
                self.unlisten(user_id, queue)
                queue.get_nowait()
                queue.put_nowait(None)

        sockets = list(self.sockets.get(user_id, ()))
        results = await asyncio.gather(
            *(self._send(ws, message) for ws in sockets), return_exceptions=True
        )
        for ws, result in zip(sockets, results):
            if result is not True:
                self.remove(user_id, ws)

    async def _send(self, websocket: WebSocket, message: dict) -> bool:
        await asyncio.wait_for(websocket.send_json(message), self.send_timeout)
        return True
