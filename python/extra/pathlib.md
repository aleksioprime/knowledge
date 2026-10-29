# Пути к файлам: `pathlib`

Путь к файлу кажется обычной строкой, пока не начинаешь с ним работать: склеить папку и имя, достать расширение, найти все `.txt` в каталоге, учесть, что в Windows другой разделитель. Со строками и `os.path` это превращается в цепочки вызовов. Модуль `pathlib` представляет путь объектом, у которого всё это — методы и свойства.

## Минимальный пример

Сохраняем отчёт по задачам и читаем его обратно:

```python
from pathlib import Path

reports = Path('data') / 'reports'
reports.mkdir(parents=True, exist_ok=True)

report = reports / 'tasks-2026-11.txt'
report.write_text('Купить хлеб\nСдать отчёт\n', encoding='utf-8')

print(report)                                         # data/reports/tasks-2026-11.txt
print(report.read_text(encoding='utf-8').splitlines())  # ['Купить хлеб', 'Сдать отчёт']
```

Оператор `/` склеивает части пути и сам ставит правильный разделитель для системы. Не нужно ни `os.path.join`, ни ручных `'/'`.

## Части пути

```python
report = Path('data/reports/tasks-2026-11.txt')

report.name     # 'tasks-2026-11.txt'
report.stem     # 'tasks-2026-11' — имя без расширения
report.suffix   # '.txt'
report.parent   # Path('data/reports')

report.with_suffix('.csv')        # data/reports/tasks-2026-11.csv
report.with_name('archive.txt')   # data/reports/archive.txt
```

## Проверки и поиск файлов

```python
report.exists()    # True
report.is_file()   # True
reports.is_dir()   # True
report.stat().st_size  # 44 — размер в байтах

sorted(p.name for p in reports.glob('*.txt'))
# ['tasks-2026-10.txt', 'tasks-2026-11.txt']

list(Path('data').rglob('*.md'))  # рекурсивно во всех вложенных папках
```

## Чтение, запись, перемещение

Для небольших файлов хватает `read_text` и `write_text`. Для больших — `open`, чтобы читать построчно и не загружать файл в память целиком:

```python
with report.open(encoding='utf-8') as f:
    for line in f:
        print(line.strip())
```

```python
old = reports / 'tasks-2026-10.txt'
new = old.rename(reports / 'old-tasks.txt')  # возвращает новый путь
new.unlink()                                 # удалить файл
new.unlink(missing_ok=True)                  # без ошибки, если файла уже нет
```

Удалить папку можно через `rmdir()`, но только пустую. Для папки с содержимым — `shutil.rmtree(path)`.

## Пути относительно своего файла

Относительный путь вроде `Path('data')` отсчитывается от **текущей папки**, из которой запустили программу, а не от папки скрипта. Если запустить скрипт из другого места, он не найдёт свои файлы. Надёжнее строить путь от расположения самого модуля:

```python
BASE_DIR = Path(__file__).resolve().parent
config = BASE_DIR / 'config.toml'
```

Так часто делают в настройках Django и FastAPI-проектов.

## Частые ошибки

- **Не указана кодировка.** `read_text()` без `encoding` использует кодировку системы, и на Windows русский текст может прочитаться кракозябрами. Всегда пишите `encoding='utf-8'`.
- **Абсолютный путь справа от `/`.** `Path('/var') / '/etc'` даст `/etc`: абсолютная часть отбрасывает всё, что было слева. Следите, чтобы части пути не начинались с `/`.
- **Путь пользователя без проверки.** Если имя файла приходит из запроса, `'../../etc/passwd'` выведет за пределы нужной папки. Проверяйте: `(base / name).resolve().is_relative_to(base.resolve())`.
- **Библиотека ждёт строку.** Почти все современные функции принимают `Path`, но если старая библиотека требует строку — `str(path)`.

## Связанные темы

- [Работа с файлами и JSON](file.md)
- [Строки и f-строки](strings.md)
- [Передача файлов по HTTP](../../web/http/file_transfer.md)
