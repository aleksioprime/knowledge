import asyncio
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractExchange, AbstractRobustConnection


class RpcServer:
    """
    RPC-сервер на основе RabbitMQ
    Слушает очередь запросов и отвечает в reply_to очереди клиента.
    """

    def __init__(self, amqp_url: str, queue_name: str = "rpc_queue"):
        """
        Инициализирует RPC-сервер
        """
        self.amqp_url = amqp_url
        self.queue_name = queue_name

        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.default_exchange: Optional[AbstractExchange] = None

    async def connect(self):
        """
        Устанавливает соединение и создаёт канал
        """
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()

        self.default_exchange = self.channel.default_exchange

    async def start(self):
        """
        Запускает прослушивание очереди RPC-запросов
        """
        await self.connect()

        # Создаём очередь (если не существует)
        queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True
        )

        print(f"Сервер RPC слушает очередь '{self.queue_name}'...")

        # Регистрируем обработчик сообщений
        await queue.consume(self.on_request)

        # Бесконечное ожидание
        await asyncio.Future()

    async def on_request(self, message: AbstractIncomingMessage):
        """
        Обработчик RPC-запроса. Получает сообщение, обрабатывает и отправляет ответ обратно клиенту.
        """
        async with message.process():  # автоматический ACK
            request_id = message.correlation_id
            body = message.body.decode()

            print(f"Поступил запрос {request_id}: {body}")

            try:
                user_id = int(body)
                response_text = f"username_for_{user_id}"
            except Exception:
                response_text = "error"

            # Подготавливаем ответ
            response = aio_pika.Message(
                body=response_text.encode(),
                correlation_id=request_id
            )

            # reply_to — это имя callback-очереди клиента
            await self.default_exchange.publish(
                response,
                routing_key=message.reply_to
            )

            print(f"Отправлен ответ: {response_text}")


async def main():
    server = RpcServer("amqp://user:password@localhost/")
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
