# Дата и время

Дата и время нужны почти везде: срок задачи, время создания записи, отметка в логе. Со строками вроде `'12.11.2026'` ничего не посчитать: ни прибавить неделю, ни сравнить два срока, ни перевести в другой часовой пояс. Модуль `datetime` из стандартной библиотеки превращает дату в объект, с которым можно делать арифметику, а модуль `time` даёт временные метки (timestamp).

## Минимальный пример

Задача создана сегодня, срок — через неделю:

```python run
from datetime import date, datetime, timedelta

created = datetime(2026, 11, 5, 9, 30)
deadline = created + timedelta(days=7)

print(deadline)                               # 2026-11-12 09:30:00
print(deadline.strftime('%d.%m.%Y %H:%M'))    # 12.11.2026 09:30
print((deadline - created).days)              # 7
print(deadline.date() == date(2026, 11, 12))  # True

parsed = datetime.strptime('2026-11-12 18:00', '%Y-%m-%d %H:%M')
print(parsed > deadline)                      # True — срок уже прошёл
```

Разница двух дат — это `timedelta`, а дату и `timedelta` можно складывать. Даты сравниваются обычными `<` и `==`, без разбора строк вручную.

## Как это работает

Основные классы модуля `datetime`:

- `date` — только дата;
- `time` — только время;
- `datetime` — дата и время вместе;
- `timedelta` — промежуток времени.

```python run session=date
from datetime import date, time, datetime, timedelta, timezone
```

### Текущая дата и время

```python run session=date
now = datetime.now()               # текущие дата и время
today = date.today()               # только дата
utc_now = datetime.now(timezone.utc)  # текущее время по UTC

print(now)
print(today)
print(utc_now)
```

Раньше время по UTC получали через `datetime.utcnow()`, но с Python 3.12 этот метод устарел (deprecated): он возвращает время без часового пояса, и его легко спутать с местным. Используйте `datetime.now(timezone.utc)`.

### Создание даты и времени вручную

```python run session=date
d = date(2025, 11, 12)
t = time(14, 30, 0)
dt = datetime(2025, 11, 12, 14, 30)

print(d)   # 2025-11-12
print(t)   # 14:30:00
print(dt)  # 2025-11-12 14:30:00
```

### Форматирование даты

Метод `strftime` превращает дату в строку по шаблону.

```python run session=date
now = datetime.now()
print(now.strftime("%Y-%m-%d %H:%M:%S"))  # год-месяц-день часы:минуты:секунды
```

### Преобразование строки в дату

Метод `strptime` делает обратное: разбирает строку по шаблону и возвращает `datetime`.

```python run session=date
s = "2025-11-12 14:30"
dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
print(dt)  # 2025-11-12 14:30:00
```

### Временная метка (timestamp)

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

### Временные зоны

```python run
from datetime import datetime, timezone, timedelta

utc = datetime.now(timezone.utc)  # текущее время по UTC
moscow = utc.astimezone(timezone(timedelta(hours=3)))

print(moscow)  # то же время с поправкой +03:00
```

## Частые ошибки

- Сравнение «наивной» даты с датой с часовым поясом → `TypeError: can't compare offset-naive and offset-aware datetimes` → храните и сравнивайте всё в UTC: `datetime.now(timezone.utc)`, а не `datetime.now()`.
- Шаблон `strptime` не совпадает со строкой (`%m` вместо `%d`, нет секунд) → `ValueError: time data ... does not match format` → подберите шаблон под строку; для ISO-формата `2026-11-12T18:00:00` используйте `datetime.fromisoformat()` без шаблона.
- Срок хранится строкой и сравнивается как текст → `'12.11.2026' < '5.11.2026'` даёт `True`, сортировка перепутана → разбирайте строку в `datetime` на входе и храните объект, а в строку переводите только для вывода.
- Прибавить месяц через `timedelta(days=30)` → 31 января плюс 30 дней — это 2 марта, а не конец февраля → у `timedelta` нет месяцев и лет; используйте `date.replace(month=...)` с проверкой дня или `dateutil.relativedelta` из сторонней библиотеки.
- Сдвиг на 3 часа руками (`now + timedelta(hours=3)`) вместо часового пояса → время «едет» при переходе на летнее время и в UTC-записях → задавайте пояс через `zoneinfo.ZoneInfo('Europe/Moscow')` и `astimezone`.

## Когда не использовать

Если дата нужна только для отображения и никаких вычислений с ней нет, объект `datetime` лишний: строку `'12.11.2026'` из базы можно вывести как есть. Так же для измерения длительности кода не нужен `datetime.now()`: разница двух вызовов зависит от смены системного времени, а `time.perf_counter()` считает ровно.

Для сложных календарных правил (последний рабочий день месяца, «через два месяца», повторяющиеся события) стандартной библиотеки мало — возьмите `dateutil` или `pendulum`. Для названий месяцев на русском и локальных форматов — модуль `babel`.

## Связанные темы

- [Строки и f-строки](strings.md) — формат даты прямо в f-строке: `f'{deadline:%d.%m.%Y}'`
- [Работа с файлами и JSON](file.md)
- [Логирование](logging.md) — отметки времени в формате записей
- [Подсказки типов](../typing/type_hints.md)
