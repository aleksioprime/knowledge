import asyncio
import uuid
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

import os

RABBITMQ_URL = os.getenv("RABBITMQ_URL")


class RpcClient:
    """
    Асинхронный RPC клиент для RabbitMQ
    Отвечает за общую логику RPC-взаимодействия по сети:
    подключение, отправку запросов, ожидание ответов, обработку таймаутов.
    Он не знает ничего конкретно о категориях.
    """

    def __init__(self, amqp_url: str = RABBITMQ_URL):
        """Инициализация RPC клиента"""
        # URL для подключения к RabbitMQ
        self.amqp_url = amqp_url
        # Инициализация переменных для соединения, канала и очереди ответов
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.callback_queue: Optional[aio_pika.Queue] = None
        # Словарь для хранения Future объектов, ожидающих ответов
        self.futures = {}
        # Получение текущего цикла событий
        self.loop = asyncio.get_running_loop()

    async def connect(self):
        """Установка соединения с RabbitMQ"""
        # Устанавливаем надежное соединение с RabbitMQ (loop используется для асинхронности)
        self.connection = await aio_pika.connect_robust(self.amqp_url, loop=self.loop)
        # Создаем канал для общения
        self.channel = await self.connection.channel()
        # Создаем временную очередь для получения ответов
        self.callback_queue = await self.channel.declare_queue(
            exclusive=True,     # очередь будет удалена после закрытия соединения
            )
        # Начинаем потреблять сообщения из этой очереди для обработки ответов
        await self.callback_queue.consume(
            self.on_response,   # функция обработки ответов
            no_ack=True,        # автоматически подтверждать получение сообщений
            )

    async def close(self):
        """Закрытие соединения с RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    def on_response(self, message: AbstractIncomingMessage):
        """Обработка ответов от сервера RPC"""
        # Извлекаем соответствующий Future по корреляционному ID
        future = self.futures.pop(message.correlation_id, None)
        # Если найден соответствующий Future, устанавливаем результат
        if future:
            future.set_result(message.body)

    async def call(self, category_id: int) -> Optional[bytes]:
        """Выполнение RPC вызова для проверки существования категории по ID"""
        # Проверяем, что соединение установлено
        if not self.connection or self.connection.is_closed:
            raise ConnectionError("RPC клиент не подключен к RabbitMQ")

        # Генерируем уникальный идентификатор для корреляции запросов и ответов
        correlation_id = str(uuid.uuid4())
        # Создаем Future для ожидания ответа
        future = self.loop.create_future()
        # Сохраняем Future с уникальным идентификатором корреляции в словаре
        self.futures[correlation_id] = future

        # Отправляем сообщение в очередь для проверки категории
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=str(category_id).encode(),     # Тело сообщения - ID категории
                correlation_id=correlation_id,      # Уникальный ID для корреляции
                reply_to=self.callback_queue.name,  # Очередь для получения ответа
            ),
            routing_key="category_check_queue",     # Очередь назначения на сервере RPC
        )

        # Ожидаем ответа с таймаутом (5 секунд)
        try:
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            # Если ответ не получен в течение таймаута, удаляем Future из словаря
            self.futures.pop(correlation_id, None)
            return None


class RabbitMQCategoryValidator:
    """
    Конкретная реализация валидатора категорий через RabbitMQ RPC
    Отвечает за специфичную бизнес-логику валидации категорий:
    он знает, какую очередь использовать (category_check_queue),
    как интерпретировать ответ (является ли b'true'подтверждением существования)
    и что делать в случае None ответа.
    """

    def __init__(self):
        """Инициализация валидатора категорий"""
        self.rpc_client = RpcClient()

    async def connect(self):
        """Установка соединения с RabbitMQ"""
        await self.rpc_client.connect()

    async def close(self):
        """Закрытие соединения с RabbitMQ"""
        await self.rpc_client.close()

    async def check_exists(self, category_id: int) -> bool:
        """Проверка существования категории по ID через RPC вызов"""
        response = await self.rpc_client.call(category_id)
        if response is None:
            return False
        return response == b'true'

# Будет создан один единственный экземпляр RabbitMQCategoryValidator на всё время жизни приложения
# Этот экземпляр открывает и закрывает соединение с RabbitMQ при старте и остановке приложения в main.py
category_validator_instance = RabbitMQCategoryValidator()