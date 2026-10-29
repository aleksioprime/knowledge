# Пул потоков

`ThreadPoolExecutor` — пул потоков, то есть заранее созданный набор рабочих потоков, которым можно поручать задачи.

Чтобы выполнить синхронную или блокирующую функцию из асинхронного кода, вызывается `loop.run_in_executor(executor, func, *args)`:

1. Корутина вызывает `run_in_executor()` и тем самым говорит циклу событий: «выполни эту синхронную функцию в отдельном потоке».
2. Задача отправляется в пул потоков: пул берёт свободный поток и запускает в нём обычную синхронную функцию.
3. Пока поток занят, цикл событий не блокируется и продолжает обслуживать другие корутины, таймеры, сокеты.
4. Поток завершает работу и записывает результат в объект Future, а asyncio возобновляет корутину с готовым значением.

`asyncio` работает в одном потоке, `ThreadPoolExecutor` создаёт дополнительные потоки, а ОС распределяет процессорное время между ними.

::: warning Примеры с пулом потоков запускайте локально
В браузере у Python нет потоков, поэтому под кодом показан вывод, полученный при локальном запуске.
:::

## Пример 1. Запись в SQLite

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

## Пример 2. Вычисления в NumPy

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

## Пример 3. Обработка изображений в OpenCV

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

## Связанные темы

- [Многозадачность в Python](README.md)
- [Асинхронность (asyncio)](async.md)
- [Потоки](multithreading.md)
