# Логирование (`logging`)

`print` хорош для быстрой отладки, но в работающем приложении его не хватает. Сообщения не отличить по важности, их нельзя отключить без правки кода, непонятно, когда и из какого модуля они пришли, а в файл они не попадают. Модуль `logging` из стандартной библиотеки решает всё это: вы один раз настраиваете, *куда* и *что* писать, а в коде просто сообщаете о событиях.

## Минимальный пример

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def send_reminder(task_title: str, email: str) -> None:
    logger.debug('Готовим письмо для %s', email)
    logger.info('Отправлено напоминание «%s» на %s', task_title, email)


send_reminder('Сдать отчёт', 'anna@example.com')
```

```text
2026-10-28 21:29:19,086 INFO app.reminders: Отправлено напоминание «Сдать отчёт» на anna@example.com
```

Сообщение `debug` не появилось: уровень `INFO` пропускает только то, что важнее отладки. Чтобы увидеть подробности, достаточно поменять одну строку в настройке — код функций трогать не нужно.

## Как это работает

В `logging` три главные роли:

- **Логгер** (`logging.getLogger(name)`) — то, во что код пишет сообщения. Логгеры образуют дерево по точкам в имени: `app.db` — потомок `app`, а `app` — потомок корневого логгера.
- **Обработчик** (handler) — куда уходит сообщение: в консоль, файл, сеть.
- **Форматтер** — как выглядит строка: время, уровень, имя логгера, текст.

Сообщение, записанное в `app.db`, «всплывает» вверх по дереву и попадает в обработчики `app` и корневого логгера. Поэтому обработчики настраивают один раз наверху, а в модулях пишут только:

```python
logger = logging.getLogger(__name__)
```

`__name__` — имя модуля, например `app.services.reminders`. По нему в логах сразу видно, откуда сообщение, и можно настроить уровень для отдельной части приложения.

### Уровни

| Уровень | Когда использовать | Пример |
|---|---|---|
| `DEBUG` | Подробности для отладки. В продакшене обычно выключен | SQL-запрос, аргументы функции |
| `INFO` | Нормальный ход работы | Приложение запущено, письмо отправлено, пользователь вошёл |
| `WARNING` | Что-то пошло не так, но работа продолжается | Медленный ответ сервиса, устаревший API, заканчивается место |
| `ERROR` | Операция не удалась, но приложение живо | Не отправилось письмо, не сохранился файл |
| `CRITICAL` | Приложение не может продолжать работу | Нет доступа к базе, сломан конфиг |

Уровень логгера работает как фильтр: всё, что ниже него, отбрасывается.

### Ошибки с трассировкой

Внутри `except` используйте `logger.exception` — он пишет сообщение уровня `ERROR` и добавляет полный traceback:

```python
try:
    progress = done / total
except ZeroDivisionError:
    logger.exception('Не удалось посчитать прогресс задачи')
```

```text
2026-10-28 21:29:19,086 ERROR app.reminders: Не удалось посчитать прогресс задачи
Traceback (most recent call last):
  File "app.py", line 19, in <module>
    progress = done / total
ZeroDivisionError: division by zero
```

### Консоль и файл одновременно

У каждого обработчика может быть свой уровень. Например, в консоль — только важное, а в файл — всё подряд:

```python
import logging

logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

file = logging.FileHandler('app.log', encoding='utf-8')
file.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
console.setFormatter(formatter)
file.setFormatter(formatter)

logger.addHandler(console)
logger.addHandler(file)

logger.debug('Только в файле')
logger.info('В консоли и в файле')
```

### Настройка словарём

В приложениях настройку обычно держат в одном месте в виде словаря. Так удобно, например, приглушить шумную библиотеку:

```python
import logging.config

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'default'},
    },
    'loggers': {
        'app': {'level': 'DEBUG', 'handlers': ['console']},
        'sqlalchemy.engine': {'level': 'WARNING'},  # без потока SQL-запросов
    },
}

logging.config.dictConfig(LOGGING)
```

## Частые ошибки

- **Сообщения не появляются.** Без настройки Python показывает только `WARNING` и выше: `logger.info(...)` молча пропадёт. Вызовите `basicConfig` или `dictConfig` при старте приложения.
- **f-строка в сообщении.** `logger.debug(f'Данные: {big_object}')` собирает строку, даже если `DEBUG` выключен. Пишите `logger.debug('Данные: %s', big_object)` — тогда строка соберётся, только если сообщение действительно будет выведено.
- **Настройка логирования в библиотечном модуле.** `basicConfig` в модуле, который импортируют другие, навязывает им свой формат. Настраивайте логирование только в точке входа приложения.
- **Сообщения дублируются.** Обработчик добавили и дочернему, и родительскому логгеру — сообщение выводится дважды из-за всплытия. Держите обработчики наверху или поставьте `logger.propagate = False`.
- **Пароли и токены в логах.** Логи читают многие и хранят долго. Не пишите туда секреты и персональные данные целиком.

## Когда не использовать

Для одноразового скрипта на 20 строк `print` проще и честнее. А когда сервисов становится несколько, одного `logging` мало: логи нужно собирать в одно место и искать по ним — это задача [централизованного логирования](../../../infrastructure/monitoring/logging/README.md).

## Связанные темы

- [Обработка исключений](../basics/exceptions.md)
- [Централизованное логирование](../../../infrastructure/monitoring/logging/README.md)
