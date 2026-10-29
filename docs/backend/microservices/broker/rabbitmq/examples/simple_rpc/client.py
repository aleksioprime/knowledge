import asyncio
import uuid
import aio_pika


class RpcClient:
    """
    Асинхронный RPC-клиент для взаимодействия с RabbitMQ по паттерну
    Request/Response (Remote Procedure Call)
    """
    def __init__(self, amqp_url: str):
        """
        Инициализация клиента RPC
        """
        self.amqp_url = amqp_url
        # Словарь для сопоставления correlation_id и Future объектов
        self.responses: dict[str, asyncio.Future] = {}
        # Инициализация соединения
        self.connection = None
        # Канал для публикации и потребления сообщений
        self.channel = None
        # Callback-очередь для получения ответов от сервера
        self.callback_queue = None

    async def connect(self):
        """
        Устанавливает подключение к RabbitMQ, создаёт канал и callback-очередь
        Callback-очередь (reply queue) — это временная очередь клиента,
        куда сервер будет отправлять ответы на RPC-запросы.
        """
        # Надёжное соединение с авто-переподключением
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        # Канал для публикации и потребления сообщений
        self.channel = await self.connection.channel()

        # Создаём эксклюзивную (анонимную) очередь под ответы.
        # Она исчезнет автоматически после закрытия соединения
        self.callback_queue = await self.channel.declare_queue(
            exclusive=True
        )

        # Подписываемся на сообщения из callback-очереди
        await self.callback_queue.consume(self.on_response)

    async def on_response(self, message: aio_pika.IncomingMessage):
        """
        Callback-функция, вызываемая при получении ответа от RPC-сервера.
        """
        async with message.process():
            # Извлекаем correlation_id из полученного сообщения
            corr_id = message.correlation_id

            # Если есть ожидающий Future с таким correlation_id...
            if corr_id in self.responses:
                # Получаем соответствующий Future и устанавливаем результат
                fut = self.responses.pop(corr_id)
                fut.set_result(message.body.decode())
            else:
                print(f"Получен неожиданный correlation_id: {corr_id}")

    async def call(self, payload: str):
        """
        Выполняет один RPC-вызов:
        """
        # Генерируем уникальный correlation_id для этого запроса
        correlation_id = str(uuid.uuid4())
        # Сохраняем future, чтобы callback мог завершить его
        future = asyncio.get_event_loop().create_future()
        self.responses[correlation_id] = future

        # Создаём AMQP-сообщение с нужными заголовками
        message = aio_pika.Message(
            body=payload.encode(),
            correlation_id=correlation_id,
            reply_to=self.callback_queue.name
        )

        # Отправляем сообщение в очередь запросов rpc_queue
        await self.channel.default_exchange.publish(
            message,
            routing_key="rpc_queue"
        )

        # Ждём, пока ответ придёт в callback_queue и будет обработан on_response(...) в течение 5 секунд иначе TimeoutError
        try:
            return await asyncio.wait_for(future, timeout=5)
        except asyncio.TimeoutError:
            self.responses.pop(correlation_id, None)
            print(f"RPC-вызов превысил timeout ожидания ответа")


async def main():
    rpc = RpcClient("amqp://user:password@localhost/")
    await rpc.connect()

    id = input("Запрос username для user_id=")
    response = await rpc.call(id)

    print(f"Ответ: {response}")

if __name__ == "__main__":
    asyncio.run(main())