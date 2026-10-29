# Работа с файлами и JSON

Программе часто нужно сохранить данные между запусками или обменяться ими с другой программой: записать настройки, прочитать список пользователей, сохранить отчёт. Для текста и байтов есть встроенная функция `open`, а для структурированных данных — формат JSON и модуль `json`.

## JSON

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

## Текстовые файлы

### Чтение

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

### Запись

Режим `"w"` создаёт файл или перезаписывает существующий. Метод `write` записывает строку, `writelines` — список строк. Символы перевода строки `\n` нужно добавлять самим.

```python run
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("Привет, мир!\n")
    f.writelines(["Строка 1\n", "Строка 2\n"])

with open("output.txt", "r", encoding="utf-8") as f:
    print(f.read())
```

## Бинарные файлы

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

## Проверка существования файла

```python run
import os

with open("data.txt", "w", encoding="utf-8") as f:
    f.write("hello")

print(os.path.exists("data.txt"))     # True
print(os.path.exists("missing.txt"))  # False
```

## Связанные темы

- [Пути к файлам: `pathlib`](pathlib.md)
- [Байты и Unicode](../master/unicode.md)
- [Строки и f-строки](strings.md)
- [Дата и время](date.md)
