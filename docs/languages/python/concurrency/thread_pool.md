# Пул потоков

Пул потоков нужен, когда в асинхронной программе есть блокирующий вызов, который нельзя переписать на `await`: старый драйвер базы данных, запись в SQLite, обработка изображения. Если вызвать такую функцию прямо в корутине, замрёт весь цикл событий. `ThreadPoolExecutor` выполняет её в отдельном потоке, а цикл тем временем обслуживает остальные задачи.

::: warning Примеры с пулом потоков запускайте локально
В браузере у Python нет потоков, поэтому под кодом показан вывод, полученный при локальном запуске.
:::

## Минимальный пример

Три блокирующих вызова по полсекунды уходят в пул и выполняются одновременно, а `main()` получает результаты через `gather()`:

```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


def fetch_user(user_id):
    time.sleep(0.5)  # блокирующий вызов: например, старая библиотека без asyncio
    return {'id': user_id, 'name': f'user{user_id}'}


async def main():
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=3) as executor:
        tasks = [loop.run_in_executor(executor, fetch_user, i) for i in range(1, 4)]
        users = await asyncio.gather(*tasks)
    print(users)


asyncio.run(main())
# [{'id': 1, 'name': 'user1'}, {'id': 2, 'name': 'user2'}, {'id': 3, 'name': 'user3'}]
```

## Как это работает

`ThreadPoolExecutor` — пул потоков, то есть заранее созданный набор рабочих потоков, которым можно поручать задачи.

Чтобы выполнить синхронную или блокирующую функцию из асинхронного кода, вызывается `loop.run_in_executor(executor, func, *args)`:

1. Корутина вызывает `run_in_executor()` и тем самым говорит циклу событий: «выполни эту синхронную функцию в отдельном потоке».
2. Задача отправляется в пул потоков: пул берёт свободный поток и запускает в нём обычную синхронную функцию.
3. Пока поток занят, цикл событий не блокируется и продолжает обслуживать другие корутины, таймеры, сокеты.
4. Поток завершает работу и записывает результат в объект Future, а asyncio возобновляет корутину с готовым значением.

`asyncio` работает в одном потоке, `ThreadPoolExecutor` создаёт дополнительные потоки, а ОС распределяет процессорное время между ними.

### Пример 1. Запись в SQLite

```python
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor

# Создаём базу
conn = sqlite3.connect('demo.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, value TEXT)')
conn.commit()
conn.close()


def insert_item(i: int):
    """Блокирующая синхронная функция"""
    conn = sqlite3.connect('demo.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO items (value) VALUES (?)', (f'Item {i}',))
    conn.commit()
    conn.close()
    return i


async def main():
    # Создаём пул потоков
    executor = ThreadPoolExecutor(max_workers=4)
    # Получаем текущий цикл событий
    loop = asyncio.get_running_loop()

    # Запускаем блокирующие операции в пуле потоков:
    # вставляем 10 элементов в базу данных
    tasks = [
        loop.run_in_executor(executor, insert_item, i)
        for i in range(10)
    ]

    # Ожидаем завершения всех задач
    results = await asyncio.gather(*tasks)
    print('Готово:', results)


asyncio.run(main())
```

```text
Готово: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

### Пример 2. Вычисления в NumPy

NumPy освобождает GIL на время тяжёлых операций, поэтому потоки здесь действительно считают параллельно.

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np


def heavy_numpy(n: int):
    """Тяжёлое вычисление в NumPy, GIL освобождается"""
    a = np.random.rand(n, n)
    b = np.random.rand(n, n)
    c = a @ b
    return float(c.mean())


async def main():
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_running_loop()

    # Выполняем 4 тяжёлые задачи параллельно
    tasks = [
        loop.run_in_executor(executor, heavy_numpy, 1200)
        for _ in range(4)
    ]

    results = await asyncio.gather(*tasks)
    print('Результаты:', results)


asyncio.run(main())
```

```text
Результаты: [299.78710612751865, 300.34833689914103, 299.596943185465, 299.61730828726365]
```

### Пример 3. Обработка изображений в OpenCV

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

import cv2


def process_image(path: str):
    """Блокирующая функция: читает и обрабатывает изображение"""
    img = cv2.imread(path)           # блокирующее обращение к диску
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (11, 11), 0)
    return blur.mean()               # возвращаем простую метрику


async def main():
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=4)

    # Запускаем 4 параллельные обработки изображения
    tasks = [
        loop.run_in_executor(executor, process_image, 'test.png')
        for _ in range(4)
    ]

    results = await asyncio.gather(*tasks)
    print('Результаты обработки:', results)


asyncio.run(main())
```

```text
Результаты обработки: [np.float64(84.04730892181396), np.float64(84.04730892181396), np.float64(84.04730892181396), np.float64(84.04730892181396)]
```

## Частые ошибки

- Блокирующая функция вызвана прямо в корутине, без `run_in_executor` → пока она работает, все остальные корутины стоят, ответы клиентам и таймеры задерживаются → отправлять такие вызовы в пул через `loop.run_in_executor()` или `asyncio.to_thread()`.
- В пул отправляют тяжёлые вычисления на чистом Python → ускорения нет: GIL пускает к байткоду один поток → использовать `ProcessPoolExecutor` или библиотеку, которая освобождает GIL (NumPy, OpenCV).
- Соединение SQLite открыто в главном потоке и используется из пула → `ProgrammingError: SQLite objects created in a thread can only be used in that same thread` → открывать соединение внутри функции-воркера, как в примере с SQLite.
- Пул создают заново на каждый вызов → потоки стартуют и останавливаются ради одной задачи, накладные расходы растут → создать один `ThreadPoolExecutor` на приложение и переиспользовать его.
- `max_workers` намного больше, чем нужно → сотни потоков борются за GIL и соединения, память растёт → ограничить размер пула числом одновременных ожиданий, которые реально нужны, а поток запросов дозировать через `asyncio.Semaphore`.

## Когда не использовать

Если для операции уже есть асинхронная библиотека (`aiohttp`, `asyncpg`, `aiofiles`), пул потоков не нужен: нативный `await` дешевле потока и не упирается в размер пула. Для тяжёлых вычислений пул потоков тоже не подходит из-за GIL: берите `ProcessPoolExecutor` или [процессы](multiprocessing.md).

Если в программе нет цикла событий, `run_in_executor` ни к чему: `ThreadPoolExecutor` можно использовать напрямую через `executor.map()` и `submit()` или вовсе обойтись [потоками](multithreading.md).

## Связанные темы

- [Многозадачность в Python](README.md)
- [Асинхронность (asyncio)](async.md)
- [Потоки](multithreading.md)
- [Процессы](multiprocessing.md)
