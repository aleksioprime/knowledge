# Дата и время

Дата и время нужны почти везде: срок задачи, время создания записи, отметка в логе. В стандартной библиотеке для этого есть модуль `datetime`, а для временных меток (timestamp) — ещё и модуль `time`.

Основные классы модуля `datetime`:

- `date` — только дата;
- `time` — только время;
- `datetime` — дата и время вместе;
- `timedelta` — промежуток времени.

```python run session=date
from datetime import date, time, datetime, timedelta, timezone
```

## Текущая дата и время

```python run session=date
now = datetime.now()               # текущие дата и время
today = date.today()               # только дата
utc_now = datetime.now(timezone.utc)  # текущее время по UTC

print(now)
print(today)
print(utc_now)
```

Раньше время по UTC получали через `datetime.utcnow()`, но с Python 3.12 этот метод устарел (deprecated): он возвращает время без часового пояса, и его легко спутать с местным. Используйте `datetime.now(timezone.utc)`.

## Создание даты и времени вручную

```python run session=date
d = date(2025, 11, 12)
t = time(14, 30, 0)
dt = datetime(2025, 11, 12, 14, 30)

print(d)   # 2025-11-12
print(t)   # 14:30:00
print(dt)  # 2025-11-12 14:30:00
```

## Форматирование даты

Метод `strftime` превращает дату в строку по шаблону.

```python run session=date
now = datetime.now()
print(now.strftime("%Y-%m-%d %H:%M:%S"))  # год-месяц-день часы:минуты:секунды
```

## Преобразование строки в дату

Метод `strptime` делает обратное: разбирает строку по шаблону и возвращает `datetime`.

```python run session=date
s = "2025-11-12 14:30"
dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
print(dt)  # 2025-11-12 14:30:00
```

## Временная метка (timestamp)

Временная метка — это число секунд, прошедших с 1 января 1970 года, 00:00:00 UTC. Этот момент называют эпохой Unix (Unix Epoch).

```python run
import time
from datetime import datetime

ts = time.time()                 # текущий timestamp в секундах
dt = datetime.fromtimestamp(ts)  # timestamp → datetime

print(ts)
print(dt)
```

Модуль `time` здесь импортирован отдельно: его имя совпадает с классом `datetime.time`, и в одном пространстве имён одно затрёт другое.

## Временные зоны

```python run
from datetime import datetime, timezone, timedelta

utc = datetime.now(timezone.utc)  # текущее время по UTC
moscow = utc.astimezone(timezone(timedelta(hours=3)))

print(moscow)  # то же время с поправкой +03:00
```

## Связанные темы

- [Строки и f-строки](strings.md)
- [Работа с файлами и JSON](file.md)
- [Подсказки типов](../typing/type_hints.md)
