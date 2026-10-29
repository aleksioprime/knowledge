# Работа с файлами и JSON

Программе часто нужно сохранить данные между запусками или обменяться ими с другой программой: записать настройки, прочитать список пользователей, сохранить отчёт. Для текста и байтов есть встроенная функция `open`, а для структурированных данных — формат JSON и модуль `json`.

## Минимальный пример

Сохраняем список задач в файл и читаем его обратно:

```python run
import json

tasks = [
    {'title': 'Купить хлеб', 'done': True},
    {'title': 'Сдать отчёт', 'done': False},
]

with open('tasks.json', 'w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

with open('tasks.json', encoding='utf-8') as f:
    loaded = json.load(f)

print(loaded[1]['title'])                    # Сдать отчёт
print(sum(task['done'] for task in loaded))  # 1
```

`with` закрывает файл сам, даже если внутри блока случится ошибка. `json.dump` пишет объект в файл, `json.load` собирает его обратно: список словарей после чтения остаётся списком словарей.

## Как это работает

### JSON

JSON — текстовый формат для словарей, списков, строк и чисел. Модуль `json` переводит объекты Python в JSON и обратно:

- `json.dumps` / `json.loads` — работают со строкой;
- `json.dump` / `json.load` — работают с файлом.

```python run
import json

# Словарь → JSON-строка
data = {"name": "Alice", "age": 25}
json_str = json.dumps(data)
print(json_str)  # {"name": "Alice", "age": 25}

# JSON-строка → словарь
json_str = '{"name": "Alice", "age": 25}'
data = json.loads(json_str)
print(data["name"])  # Alice

# Запись JSON в файл
data = {"city": "Moscow", "temp": -5}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Чтение JSON из файла
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
print(data["city"])  # Moscow
```

Параметр `ensure_ascii=False` сохраняет кириллицу как есть, а не в виде `\uXXXX`. Параметр `indent=2` добавляет отступы, чтобы файл было удобно читать.

Так же сохраняется и список словарей — например, список пользователей:

```python run
import json

users = [
    {"id": 1, "name": "Alice", "age": 25},
    {"id": 2, "name": "Bob", "age": 30},
    {"id": 3, "name": "Eve", "age": 22}
]

with open("users.json", "w", encoding="utf-8") as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

with open("users.json", "r", encoding="utf-8") as f:
    loaded_users = json.load(f)

print(loaded_users[1]["name"])  # Bob
```

### Текстовые файлы

#### Чтение

Файл можно прочитать целиком, по одной строке или сразу списком строк. После чтения указатель стоит в конце файла, поэтому перед следующим чтением его возвращают в начало методом `seek(0)`.

```python run
from pathlib import Path

Path("data.txt").write_text("Первая строка\nВторая строка\nТретья строка\n", encoding="utf-8")

with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()       # весь файл одной строкой
    f.seek(0)
    line = f.readline()   # одна строка
    f.seek(0)
    lines = f.readlines() # список строк

print(repr(text))
print(repr(line))  # 'Первая строка\n'
print(lines)       # ['Первая строка\n', 'Вторая строка\n', 'Третья строка\n']
```

#### Запись

Режим `"w"` создаёт файл или перезаписывает существующий. Метод `write` записывает строку, `writelines` — список строк. Символы перевода строки `\n` нужно добавлять самим.

```python run
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("Привет, мир!\n")
    f.writelines(["Строка 1\n", "Строка 2\n"])

with open("output.txt", "r", encoding="utf-8") as f:
    print(f.read())
```

### Бинарные файлы

Картинки, архивы и другие нетекстовые файлы открывают в бинарном режиме — `"rb"` и `"wb"`. Тогда `read` возвращает `bytes`, а не строку, и кодировка не нужна.

::: warning Этот пример запускайте локально
Ему нужен файл `image.png` рядом со скриптом.
:::

```python
with open("image.png", "rb") as f:
    data = f.read()

with open("copy.png", "wb") as f:
    f.write(data)
```

### Проверка существования файла

```python run
import os

with open("data.txt", "w", encoding="utf-8") as f:
    f.write("hello")

print(os.path.exists("data.txt"))     # True
print(os.path.exists("missing.txt"))  # False
```

## Частые ошибки

- Файл открыт без `encoding` → на Windows русский текст читается «кракозябрами» или падает с `UnicodeDecodeError` → всегда передавайте `encoding='utf-8'` и при чтении, и при записи.
- `open` без `with` и без `close()` → данные не доехали до диска, файл остался занят → открывайте файл через `with`: он закроется сам, даже при ошибке внутри.
- Режим `"w"` там, где нужно дописать → старое содержимое стёрто при каждом запуске → для добавления в конец используйте `"a"`, для чтения и записи одного файла — `"r+"`.
- `json.dump` получает `datetime`, `Decimal` или `set` → `TypeError: Object of type datetime is not JSON serializable` → переводите такие значения в строку или число заранее либо передайте `default=str`.
- Второй `f.read()` подряд возвращает пустую строку → после первого чтения указатель стоит в конце файла → верните его в начало `f.seek(0)` или прочитайте файл один раз и работайте с результатом.
- `json.loads` для файла или `json.load` для строки → `TypeError` или `JSONDecodeError` на первом символе → `loads`/`dumps` работают со строкой, `load`/`dump` — с открытым файлом.

## Когда не использовать

JSON — не универсальное хранилище. Если данные надо искать, фильтровать и менять по частям, а не перезаписывать файл целиком, возьмите SQLite (модуль `sqlite3`) или другую [базу данных](../../../backend/databases/README.md). Для таблиц, которые откроют в Excel, подойдёт модуль `csv`; для настроек проекта в Python принят TOML и модуль `tomllib`.

Читать большой файл через `read()` или `readlines()` не стоит: он целиком попадёт в память. Проходите по файлу строка за строкой (`for line in f`), а для путей, расширений и поиска файлов по маске удобнее [`pathlib`](pathlib.md), чем `os.path` и склейка строк.

## Связанные темы

- [Пути к файлам: `pathlib`](pathlib.md)
- [Байты и Unicode](../advanced/unicode.md)
- [Строки и f-строки](strings.md)
- [Дата и время](date.md)
