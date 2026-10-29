# Celery: первая фоновая задача

Пользователь нажимает «Зарегистрироваться», а сервер ещё две секунды отправляет приветственное письмо. Всё это время пользователь смотрит на крутящийся индикатор, а если почтовый сервер недоступен, регистрация вообще падает с ошибкой. Долгие и ненадёжные операции лучше вынести **в фон**: API ставит задачу в очередь и сразу отвечает, а отдельный процесс-воркер выполняет её, когда сможет. Celery — самый распространённый инструмент для этого в Python.

```bash
pip install "celery[redis]"
docker run -d --name redis -p 6379:6379 redis:7.4
```

## Минимальный пример

```python
# tasks.py
import time

from celery import Celery

app = Celery('demo', broker='redis://localhost:6379/5', backend='redis://localhost:6379/6')


@app.task
def send_email(to: str, subject: str) -> str:
    time.sleep(2)  # будто бы долго говорим с почтовым сервером
    return f'отправлено {to}'
```

Запускаем воркер в отдельном терминале:

```bash
celery -A tasks worker --loglevel=info
```

И ставим задачу:

```python
from tasks import send_email

result = send_email.delay('anna@example.com', 'Срок задачи — завтра')
# delay вернулся за 0.15 с, задача ещё выполняется: result.status == 'PENDING'

result.get(timeout=10)  # 'отправлено anna@example.com' — ждём результат, только если он нужен
result.status           # 'SUCCESS'
```

`delay` возвращается почти мгновенно, а две секунды работы уходят в воркер.

## Как это работает

В схеме три участника:

- **приложение** (producer) — вызывает `send_email.delay(...)`. Celery превращает вызов в сообщение: имя задачи и аргументы в JSON;
- **брокер** — очередь сообщений, здесь Redis. Можно использовать и RabbitMQ;
- **воркер** — отдельный процесс, который забирает сообщения из брокера и выполняет функции.

Результат по умолчанию никуда не сохраняется. Если он нужен, задают **result backend** (здесь Redis, база 6). Для задач вроде «отправь письмо» результат обычно не нужен, и backend можно не настраивать.

Воркер и приложение — разные процессы, часто на разных машинах. Поэтому:

- **аргументы должны сериализоваться в JSON.** Передавайте `task_id`, а не объект SQLAlchemy или открытый файл;
- **задача должна сама получить свежие данные.** Пока задача ждала в очереди, объект мог измениться или исчезнуть.

## Напоминания в «Задачнике»

В [«Задачнике»](../../../practice/projects/tasker/README.md) Celery рассылает напоминания о задачах, срок которых наступает завтра:

```python
# app/worker.py
celery_app = Celery('tasker', broker=settings.celery_broker_url)
celery_app.conf.update(timezone='Europe/Moscow', task_acks_late=True)


@celery_app.task
def remind_about_due_tasks() -> int:
    task_ids = asyncio.run(_find_tasks_to_remind())
    for task_id in task_ids:
        send_reminder.delay(task_id)
    return len(task_ids)


@celery_app.task(autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=5)
def send_reminder(task_id: int) -> bool:
    return asyncio.run(_send_reminder(task_id))
```

Одна задача находит id подходящих задач, а для каждой ставит отдельную задачу на отправку. Если одно письмо не уйдёт, остальные отправятся, а неудачное повторится само.

Сама логика лежит в сервисе и не зависит от Celery, поэтому её легко тестировать:

```python
# app/services/reminders.py
async def send_reminder(session: AsyncSession, task_id: int) -> bool:
    task = await session.scalar(select(Task).options(selectinload(Task.owner)).where(Task.id == task_id))
    # Задачу могли выполнить или уже напомнить о ней: повторный запуск ничего не сломает
    if task is None or task.done or task.reminder_sent:
        return False
    send_email(task.owner.email, 'Срок задачи — завтра', task.title)
    task.reminder_sent = True
    await session.commit()
    return True
```

Запуск в Docker и ручной вызов:

```bash
docker compose up -d
docker compose exec worker celery -A app.worker call app.worker.remind_about_due_tasks
docker compose logs worker
```

```text
Task app.worker.remind_about_due_tasks[2e4f4131...] received
Task app.worker.send_reminder[3f41ec23...] received
Task app.worker.remind_about_due_tasks[2e4f4131...] succeeded in 0.07s: 1
Письмо для anna@example.com: Срок задачи — завтра — Сдать отчёт
Task app.worker.send_reminder[3f41ec23...] succeeded in 0.05s: True
```

Повторный вызов вернёт `0`: напоминание уже отправлено (`reminder_sent`).

## Асинхронный код внутри задачи

Задачи Celery — обычные синхронные функции. Если приложение использует асинхронный SQLAlchemy, внутри задачи запускают свой цикл событий через `asyncio.run(...)`. Каждый вызов создаёт новый цикл, а соединения пула привязаны к циклу, в котором открыты. Поэтому движок для воркера создают без пула:

```python
engine = create_async_engine(settings.database_url, poolclass=NullPool)
```

## Частые ошибки

- **Задача не идемпотентна.** Celery гарантирует доставку «хотя бы один раз»: при падении воркера (особенно с `task_acks_late=True`) задача выполнится повторно. Пишите задачи так, чтобы второй запуск ничего не портил — как флаг `reminder_sent` выше.
- **Вызов без `.delay`.** `send_email('anna@example.com', ...)` выполнит функцию сразу, в текущем процессе, без всякой очереди.
- **Объект вместо id в аргументах.** `send_reminder.delay(task)` упадёт на сериализации или передаст устаревшие данные. Передавайте `task.id`.
- **Задача поставлена до `commit`.** Воркер может взять задачу раньше, чем транзакция сохранит данные, и не найти запись. Ставьте задачу после `commit`.
- **Воркер на macOS падает с `ValueError: not enough values to unpack (expected 3, got 0)`.** Это известная проблема пула процессов `prefork` на macOS. Для локальной разработки запускайте `celery -A tasks worker --pool=threads` (или `--pool=solo`). В Docker на Linux такой проблемы нет.

## Связанные темы

- [Повторы, расписание и цепочки задач](retries_beat_canvas.md)
- [Dramatiq](../dramatiq/README.md) — более простая альтернатива
- [Redis как очередь](../../databases/redis/scenarios.md#5-очередь-заданий)
