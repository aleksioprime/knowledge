# Процессы в Python

В Python процессы применяют, чтобы распараллелить тяжёлые вычисления: подсчёт хэшей, работу с матрицами, обработку изображений.

::: warning Примеры с процессами запускайте локально
В браузере Python не может создавать процессы, поэтому под кодом показан вывод, полученный при локальном запуске.
:::

## Точка входа

Точку входа в программу нужно отделить. При создании процесса запускается новый интерпретатор Python. Загрузив модули, он выполняет код на их верхнем уровне. Если убрать `if __name__ == '__main__':`, процессы начнут создаваться рекурсивно и получится fork-бомба. К счастью, Python не запустит программу без явной точки входа и не даст процессу уйти в рекурсию.

```python
# Код из demo/mp_demo_1.py
import time
import os

import multiprocessing as mp
from multiprocessing import Process


# Функция, которая будет работать в отдельном процессе
def printer(name):
    time.sleep(10)
    print('Привет', name)


if __name__ == '__main__':
    # Нужно для запуска в Jupyter Notebook
    mp.set_start_method('fork', force=True)
    # Создаём объект процесса, передав в него функцию и аргументы, с которыми она будет вызвана
    p = Process(target=printer, args=('Алиса',))
    p.start()
    print('Пока выполняется процесс, съешьте ещё этих мягких французских булок да выпейте чаю ☕️')
    # Process ID текущего процесса и только что запущенного
    print('Главный PID', os.getpid())
    print('Дочерний PID', p.pid)
    # Дожидаемся завершения процесса
    p.join()
    print('Завершение работы')
```

```text
Пока выполняется процесс, съешьте ещё этих мягких французских булок да выпейте чаю ☕️
Главный PID 57336
Дочерний PID 61197
Привет Алиса
Завершение работы
```

Программа ждёт завершения всех обычных дочерних процессов, прежде чем завершиться сама. Процессы-демоны работают в фоне и завершаются вместе с родительским, поэтому, чтобы дождаться демона, нужен `p.join()`.

## Как выглядят процессы в системе

```sh
(base) aleksioprime@gymnmac knowledge % ps aux | grep 60262
aleksioprime     60441   0.0  0.0 435299840   1264 s004  R+   12:47PM   0:00.00 grep 60262
aleksioprime     60262   0.0  0.1 410320928   8480 s002  S+   12:47PM   0:00.05 /opt/anaconda3/bin/python mp_demo_1.py
(base) aleksioprime@gymnmac knowledge % ps aux | grep 60715
aleksioprime     60743   0.0  0.0 435298848    864 s004  R+   12:47PM   0:00.00 grep 60715
aleksioprime     60715   0.0  0.2 410752032  15520 s002  S+   12:47PM   0:00.04 /opt/anaconda3/bin/python -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=4, pipe_handle=6) --multiprocessing-fork
```

Главному процессу интерпретатор получает имя файла. Дочернему процессу (при запуске методом spawn) передаётся код `-c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=4, pipe_handle=6)`:

- `pipe_handle` — номер файлового дескриптора, через который дочерний процесс читает данные от родителя (через pipe);
- `tracker_fd` — дескриптор для связи с `resource_tracker`, который следит за разделяемыми ресурсами (shared memory, семафорами и некоторыми shared-объектами) и чистит их, чтобы не было утечек системных ресурсов.

Флаг `--multiprocessing-fork` — внутренний маркер `multiprocessing`: процесс запущен служебным механизмом как дочерний. Несмотря на название, он применяется не только при fork.

Дочернему процессу можно передавать только объекты, которые сериализуются в байты и обратно. Для этого используется модуль `pickle`, который в основном работает с примитивными данными.

## Очереди

Очереди позволяют обмениваться сообщениями сразу между группами процессов.

```python
import multiprocessing as mp

from multiprocessing import Process
from multiprocessing.queues import Queue
from time import sleep


def producer(queue: Queue):
    # Процесс-производитель пишет сообщения в очередь
    while True:
        message = 'ping'
        queue.put(message)
        sleep(1)


def consumer(queue: Queue):
    # Процесс-потребитель читает сообщения из очереди и печатает их
    while message := queue.get():
        print(message)


if __name__ == '__main__':
    # Контекст spawn: новый процесс запускается отдельным интерпретатором Python
    ctx = mp.get_context('spawn')
    # Очередь для обмена сообщениями между процессами
    queue = Queue(ctx=ctx)
    # Каждому процессу передаём ссылку на очередь
    producer_ = Process(target=producer, args=(queue,))
    consumer_ = Process(target=consumer, args=(queue,))
    # Один процесс пишет в очередь ping, другой вычитывает и печатает.
    # Оба работают бесконечно — остановите их через Ctrl+C
    producer_.start()
    consumer_.start()
    producer_.join()
    consumer_.join()
```

```text
ping
ping
ping
...
```

## Связанные темы

- [Многозадачность в Python](README.md)
- [Потоки](multithreading.md)
- [Пример из заметки: demo/mp_demo_1.py](examples/mp_demo_1.py)
