В Celery очереди (queues) используются для организации и управления задачами. Они позволяют группировать задачи по типу, приоритету или другим критериям, что упрощает их обработку и управление.

**Основные концепции очередей в Celery:**

- **Очередь как FIFO структура данных:** Очередь — это структура данных “первым поступил, первым обслуживается” (FIFO - First-In, First-Out). Задачи добавляются в конец очереди и извлекаются из начала.
- **Множество очередей:** В Celery можно использовать несколько очередей для организации задач. Это позволяет разделить задачи по типу или приоритету. Например, можно иметь очередь для задач высокого приоритета и очередь для задач низкого приоритета.
- **Назначение задач в очереди:** При отправке задачи можно указать, в какую очередь она должна быть помещена. Это делается с помощью аргумента  `queue` в методе `apply_async()`.
- **Рабочие и очереди:** Рабочие (workers) подключаются к определенным очередям и извлекают задачи из этих очередей. Один рабочий может подключаться к нескольким очередям.
- **Имя очереди:** Очереди имеют имена, которые используются для их идентификации. Имена очередей обычно являются строками. По умолчанию используется очередь с именем  `celery`.
- **Routers (маршрутизаторы):** Более сложные сценарии могут использовать маршрутизаторы (routers) для динамического назначения задач в очереди на основе атрибутов задачи.

**Пример использования очередей:**

```python
from celery import Celery
from celery.utils.nodenames import default_nodename

app = Celery(
	'tasks', 
	broker='redis://localhost', 
	worker_hijack_root_logger=False) # Используем Redis как брокер

@app.task(queue='high_priority')
def high_priority_task():
    print("Выполнение задачи высокого приоритета")

@app.task(queue='low_priority')
def low_priority_task():
    print("Выполнение задачи низкого приоритета")


# Запуск задач
high_priority_task.apply_async()
low_priority_task.apply_async()
```

Эти очереди сильно напоминают принцип FIFO (First In First Out), но это не совсем так. Задачи, которые сначала помещаются в очередь, первыми удаляются из очереди, но они не обязательно выполняются первыми.

В Celery задачи (tasks) — это функции Python, которые выполняются асинхронно в фоновом режиме. Они являются основными единицами работы в системе Celery. Задачи определяются с помощью декоратора  `@celery.task` и могут быть выполнены обработчиками (workers) из очереди (queue).

Пример реализации задач в FastAPI:

```python
import time

from celery import Celery
from fastapi import FastAPI

app = FastAPI()

celery = Celery(
    __name__,
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
    broker_connection_retry_on_startup=True
)


@celery.task
def call_background_task(message):
    time.sleep(10)
    print(f"Background Task called!")
    print(message)


@app.get("/")
async def hello_world(message: str):
    call_background_task.delay(message)
    return {'message': 'Hello World!'}
```

Основная цель экземпляра Celery — аннотировать методы Python, чтобы они стали задачами. Экземпляр Celery имеет декоратор `task()`, который мы можем применять ко всем вызываемым процедурам, которые мы хотим определить как асинхронные задачи. Частью декоратора `task()` является имя задачи, необязательное уникальное имя, состоящее из пакета, имен модулей и имени метода транзакции.

Например:

```python
@celery.task(name="my_first.tasks", auto_retry=[ValueError, TypeError], max_retries=5)
```

Данная задача имеет только пять повторных попыток выполнения, если во время выполнения она сталкивается с ValueError или TypeError.

В Celery есть три основных способа вызова задач: `apply_async`, `delay` и `call`. Хотя `call` может показаться простым вызовом функции, он имеет важные отличия от асинхронных вариантов.

**1. `apply_async()`:**

```python
call_background_task.apply_async(args=[arg1_value], kwargs={'key': 'value'})
```

Это наиболее гибкий и мощный способ вызова задач. Он позволяет управлять многими параметрами задачи, включая очередь, маршрутизацию, приоритет, и другие настройки. Вызов  `apply_async()` всегда асинхронный — он не блокирует выполнение кода.

**2. `delay()`:**

Это более компактный синтаксис для  `apply_async()`, который упрощает вызов задач с простыми аргументами. Он также всегда асинхронный.

```python
call_background_task.delay(arg1_value, arg2_value)
```

**3. `call()`:**

Это синхронный вызов задачи. Он блокирует выполнение кода до тех пор, пока задача не завершится. Он не использует брокер и рабочие процессы — задача выполняется в том же процессе, где вызывается  `call()`. Практически это просто вызов функции. В Celery этот способ редко используется, потому что он лишает всех преимуществ асинхронной обработки задач.

```python
call_background_task(arg1_value, arg2_value)
```

Разделение файлов на `main.py`и `task.py`

```python
from fastapi import FastAPI
from celery import Celery
from task import call_background_task

app = FastAPI()

celery = Celery(
    __name__,
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
    broker_connection_retry_on_startup=True
)


@app.get("/")
async def hello_world(message: str):
    call_background_task.delay(message)
    return {'message': 'Hello World!'}
```

```python
import time
from celery import shared_task

@shared_task()
def call_background_task(message):
    time.sleep(10)
    print(f"Background Task called!")
    print(message)
```

Вместо того, чтобы использовать `@celery.task`, мы используем декоратор `@shared_task`. Если мы этого не сделаем, это приведет к проблеме круговой зависимости. `main.py` потребуется `tasks.py` для определения функции `call_background_task`, а `task.py` потребуется экземпляр Celery, импортированный из `main.py`