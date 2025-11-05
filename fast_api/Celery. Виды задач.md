### 1. Выполнить задачу через N времени.

```python
call_background_task.apply_async(args=[message], countdown=60*5)
```

Метод `apply_async()` в Celery с параметром `countdown` — это простой и удобный способ запланировать выполнение задачи на заданное количество секунд в будущем. Он идеально подходит для ситуаций, когда вам нужно выполнить задачу через определённый промежуток времени после отправки запроса, без указания конкретного времени выполнения.

Когда вы вызываете `apply_async()` с параметром `countdown`, Celery не выполняет задачу немедленно. Вместо этого, он отправляет задачу в брокер (например, Redis или RabbitMQ), устанавливая для нее флаг задержки. Брокер хранит задачу до тех пор, пока не пройдет указанное в  `countdown` количество секунд. После этого брокер поместит задачу в очередь для выполнения рабочим (worker).

### 2. Выполнить задачу в определенное время

Для выполнения задачи в Celery в определенное время, используется параметр `eta` в методе `apply_async()`. Он принимает объект  `datetime`, указывающий точное время выполнения задачи.

```python
@app.get("/")
async def hello_world(message: str):
    task_datetime = datetime.now(timezone.utc) + timedelta(minutes=10)
    call_background_task.apply_async(args=[message], eta=task_datetime)
    return {'message': 'Hello World!'}
```

В данном случае мы говорим установить время выполнения задачи, время сейчас + 10 минут. Основное отличие от метода `countdown` в том, что в параметре `eta` мы должны указать дату и время.

### 3. Периодические задачи

В Celery периодические задачи (periodic tasks) — это задачи, которые выполняются автоматически через определённые интервалы времени или в запланированные моменты. Для их реализации в Celery используется компонент  `celery beat`.

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
    call_background_task.apply_async(args=[message], expires=3600)
    return {'message': 'Hello World!'}


celery.conf.beat_schedule = {
    'run-me-background-task': {
        'task': 'task.call_background_task',
        'schedule': 60.0,
        'args': ('Test text message',)
    }
}
```

В конфигурации мы указываем `beat_schedule` запускать нашу функцию `call_background_task()` каждые 60 секунд. Функция для запуска указывается как <имя модуля>.<имя функции>. 

Запустим это с помощью этой команды в новом окне терминала:

```sh
celery -A main.celery beat --loglevel=info
```

То есть на данный момент у нас будут запущены следующие процессы - `uvicorn`, `redis`, `celery worker` и `celery beat`.

`task.call_background_task` запускается каждые 60 секунд, используя брокер Redis. И именно Celery Beat отправляет задачу `task.call_background_task` в очередь Redis каждые 60 секунд.

Также есть еще один способ работать с запланированными задачами, это использовать Crontab Schedules из Celery Вeat:

```python
celery.conf.beat_schedule = {
    'run-me-background-task': {
        'task': 'task.call_background_task',
        'schedule': crontab(hour=7, minute=0),
        'args': ('Test text message',)
    }
}
```

Здесь мы запускаем `task.call_background_task` каждый день в 7:00.

###  Мониторинг задач

_Flower —_ это инструмент мониторинга Celery, который наблюдает и контролирует выполнение всех задач, генерируя аудит в реальном времени на веб-платформе. Но сначала нам нужно установить его с помощью _pip_:

```cmake
pip install flower
```

 Не забываем, что у нас должны быть запущены Unicorn/Uvicorn, Celery, Redis, и Celery Beat. Затем мы запускаем следующую команду Сelery с опцией flower: 

```sh
celery -A main.celery flower
```

Пройдите по URL-адресу [http://localhost:5555](http://localhost:5555/) в своем браузере. Вы увидите активные процессы Celery и статистику асинхронных заданий.

Flower — это простой и удобный веб-интерфейс для мониторинга Celery в реальном времени. Он позволяет отслеживать выполнение задач, управлять пулом воркеров (увеличивать/уменьшать), а также просматривать графики и статистику.

Документация по мониторинговому инструменту Flower находится на странице [https://flower.readthedocs.io/](https://flower.readthedocs.io/).