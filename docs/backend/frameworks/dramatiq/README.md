# Dramatiq

Задача та же, что у [Celery](../celery/README.md): вынести долгую работу в фон. Dramatiq решает её с меньшим количеством настроек. Задача — это функция с декоратором, повторы при ошибках включены сразу, а поведение настраивается понятными middleware. Если не нужны цепочки задач и встроенное расписание, Dramatiq часто проще.

```bash
pip install "dramatiq[redis]"
```

## Минимальный пример

```python
# actors.py
import time

import dramatiq
from dramatiq.brokers.redis import RedisBroker

dramatiq.set_broker(RedisBroker(url='redis://localhost:6379/7'))


@dramatiq.actor
def send_email(to: str, subject: str) -> None:
    time.sleep(2)
    print(f'отправлено {to}')
```

```bash
dramatiq actors --processes 1 --threads 4
```

```python
from actors import send_email

send_email.send('anna@example.com', 'Срок задачи — завтра')  # вернулся за 0.01 с
```

`.send()` — аналог `.delay()` в Celery: кладёт сообщение в очередь и сразу возвращается.

## Как это работает

Схема та же: приложение отправляет сообщение в брокер (Redis или RabbitMQ), а воркер его выполняет. Функция с `@dramatiq.actor` называется **актором**.

Главное отличие от Celery — **middleware**, которые включены по умолчанию:

| Middleware | Что делает | По умолчанию |
|---|---|---|
| `Retries` | повторяет задачу при **любом** исключении | до 20 раз, пауза от 15 секунд до 7 дней |
| `TimeLimit` | прерывает слишком долгую задачу | 10 минут |
| `AgeLimit` | выбрасывает слишком старые сообщения | выключен, задаётся `max_age` |
| `Prometheus` | отдаёт метрики воркера | HTTP на порту 9191 |
| `Callbacks`, `Pipelines` | `on_success`, `on_failure` и простые цепочки | — |

## Повторы

Повтор при любой ошибке — удобно для сетевых сбоев, но опасно для ошибок в коде: опечатка будет повторяться неделю. Поэтому условие повтора лучше задать явно:

```python
@dramatiq.actor(
    min_backoff=1000,   # мс
    max_backoff=10_000,
    retry_when=lambda retries, error: retries < 3 and isinstance(error, ConnectionError),
)
def flaky_send(to: str) -> str:
    ...
```

```text
попытка 1
Retrying message 'daf68a25-...' in 604 milliseconds.
попытка 2
Retrying message 'daf68a25-...' in 1928 milliseconds.
попытка 3
```

Пауза растёт экспоненциально и со случайным разбросом, поэтому первая может оказаться меньше `min_backoff`.

**`retry_when` важнее `max_retries`.** Если задан `retry_when`, то `max_retries` игнорируется. Условие `isinstance(error, ConnectionError)` без проверки `retries` будет повторять задачу бесконечно, пока сервер недоступен.

## Результаты

По умолчанию результат актора никуда не сохраняется. Если он нужен, подключают middleware `Results`:

```python
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

broker = RedisBroker(url='redis://localhost:6379/7')
broker.add_middleware(Results(backend=RedisBackend(url='redis://localhost:6379/8')))
dramatiq.set_broker(broker)


@dramatiq.actor(store_results=True)
def send_email(to: str, subject: str) -> str:
    return f'отправлено {to}'


message = send_email.send('anna@example.com', 'Отчёт')
message.get_result(block=True, timeout=10_000)  # 'отправлено anna@example.com'
```

## Celery или Dramatiq

| | Celery | Dramatiq |
|---|---|---|
| Расписание | встроенный Celery Beat | нет, нужен внешний планировщик: cron, APScheduler, `periodiq` |
| Цепочки и группы | `chain`, `group`, `chord` | `pipeline` и `group`, проще и беднее |
| Повторы | включаются явно | включены для всех ошибок сразу |
| Ограничение времени | настраивается | 10 минут по умолчанию |
| Настройка | много параметров, сложнее разобраться | мало параметров, понятные значения по умолчанию |
| Экосистема | огромная: Flower, интеграции, статьи | меньше |

Если нужно расписание, сложные сценарии из нескольких шагов или в команде уже знают Celery — берите Celery. Если нужны просто надёжные фоновые задачи с повторами — Dramatiq даст их с меньшими усилиями.

## Частые ошибки

- **Повторы ошибок в коде.** Без `retry_when` или `throws=(ValueError,)` задача с багом будет повторяться до 20 раз с паузами до недели.
- **Задача дольше 10 минут.** `TimeLimit` прервёт её на середине. Для длинных задач задайте `time_limit` явно или разбейте их на части.
- **Импорт актора до настройки брокера.** `@dramatiq.actor` привязывается к брокеру, который установлен в момент импорта. Вызывайте `set_broker` до объявления акторов.
- **Неидемпотентные задачи.** Как и в Celery, сообщение может обработаться повторно. Проверяйте, не сделана ли работа уже.

## Когда не использовать

Если нужны расписание, цепочки из многих шагов с объединением результатов или в команде уже используют Celery — берите [Celery](../celery/README.md): Dramatiq придётся дополнять внешним планировщиком и самодельной оркестрацией. Смешивать два планировщика задач в одном проекте тоже не стоит.

Для короткой работы, которую не жалко потерять при перезапуске (отправить письмо после ответа, записать метрику), очередь с брокером избыточна — хватит `BackgroundTasks` в FastAPI или пула потоков. А если задача — это реакция на события других сервисов, нужен не планировщик задач, а потребитель у брокера: [RabbitMQ](../../microservices/broker/rabbitmq/README.md) или Kafka.

## Связанные темы

- [Celery](../celery/README.md)
- [Redis как брокер](../../databases/redis/README.md)
- [RabbitMQ](../../microservices/broker/rabbitmq/README.md)
