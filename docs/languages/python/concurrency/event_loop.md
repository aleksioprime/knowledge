# Цикл событий своими руками

`asyncio` выглядит магией, пока не видно, кто и когда переключает корутины. Чтобы понять, как это устроено, полезно собрать упрощённый цикл событий самому: на генераторах вместо корутин и на модуле `selectors` для ожидания сокетов. Готовый echo-сервер в конце работает на этом самодельном цикле.

Как ведёт себя настоящий цикл asyncio, по шагам показано в заметке [Цикл событий asyncio наглядно](event_loop_visual.md).

## Минимальный пример

Вся идея цикла событий умещается в очередь и `yield`: задача делает шаг, отдаёт управление и встаёт в конец очереди.

```python run
from collections import deque


def worker(name, steps):
    for step in range(1, steps + 1):
        print(f'{name}: шаг {step}')
        yield  # отдаём управление планировщику


ready = deque([worker('задача A', 2), worker('задача B', 3)])
while ready:
    task = ready.popleft()
    try:
        next(task)
        ready.append(task)  # задача не закончилась — в конец очереди
    except StopIteration:
        pass
# задача A: шаг 1
# задача B: шаг 1
# задача A: шаг 2
# задача B: шаг 2
# задача B: шаг 3
```

Дальше эта схема обрастает деталями: системные вызовы, стек вложенных генераторов и ожидание сокетов через `selectors`.

## Как это работает

### 1. Системные вызовы и создание задач

Здесь задаётся базовый интерфейс `SystemCall`. Любой объект-наследник `SystemCall`, который корутина отдаёт через `yield`, перехватывается планировщиком и обрабатывается отдельно.

`NewTask` — конкретный системный вызов: он регистрирует новую корутину в `Scheduler`, получает её `tid` и возвращает управление родительской задаче.

```python run session=scheduler
from __future__ import annotations

from typing import Generator


class SystemCall:
    def handle(self, sched: Scheduler, task: Task):
        """
        Базовый класс для системных вызовов.
        Системные вызовы — это специальные объекты, которые задачи могут "вызывать" (yield),
        чтобы взаимодействовать с планировщиком и операционной системой.
        Метод handle() переопределяется в подклассах для конкретного поведения системного вызова.
        """
        pass


class NewTask(SystemCall):
    def __init__(self, target: Generator):
        self.target = target

    def handle(self, sched: Scheduler, task: Task):
        """Этот системный вызов создаёт новую задачу из генератора (корутины)."""
        tid = sched.add_task(self.target)
        task.sendval = tid
        sched.schedule(task)
```

### 2. Объект Task и выполнение корутин

`Task` хранит состояние одной корутины: идентификатор, текущее значение для `send`, активный генератор и стек вложенных генераторов.

Метод `run()` выполняет задачу до ближайшей точки переключения:

- если корутина вернула `SystemCall`, выполнение передаётся планировщику;
- если корутина вернула другой генератор, он кладётся на стек как вложенный вызов;
- при завершении генератора (`StopIteration`) управление возвращается на предыдущий уровень стека.

```python run session=scheduler
import types
from typing import Generator


class Task:
    # Счётчик для присвоения уникального id каждой задаче
    task_id = 0

    def __init__(self, target: Generator):
        Task.task_id += 1
        self.tid = Task.task_id      # уникальный идентификатор задачи
        self.target = target         # текущий активный генератор (корутина)
        self.sendval = None          # значение, которое будет отправлено в генератор через send()
        self.stack = []              # стек вложенных генераторов (для поддержки yield из yield)

    def run(self):
        """
        Выполняет задачу до следующего переключения управления.
        Поддерживает вложенные генераторы (корутины),
        реализуя простейший механизм кооперативного планировщика.
        """
        while True:
            try:
                # Передаём значение в текущий генератор
                # и получаем то, что он "вернул" через yield
                result = self.target.send(self.sendval)

                # Генератор вернул SystemCall — значит, он хочет выполнить системный вызов
                if isinstance(result, SystemCall):
                    return result

                # Генератор вернул другой генератор — значит, произошёл вызов вложенной корутины
                if isinstance(result, types.GeneratorType):
                    # Сохраняем текущий генератор в стек,
                    # чтобы вернуться к нему после завершения вложенного
                    self.stack.append(self.target)

                    # Начинаем выполнение вложенного генератора
                    self.target = result
                    self.sendval = None

                else:
                    # Результат не генератор — значит, корутина просто вернула значение через yield
                    if not self.stack:
                        # Стек пуст — это верхний генератор, задача завершена
                        return

                    # Передаём результат обратно родительскому генератору
                    self.sendval = result
                    self.target = self.stack.pop()

            except StopIteration:
                # Генератор завершился (вызван return или дошёл до конца)
                if not self.stack:
                    # Это был верхний генератор — задача полностью завершена
                    raise

                # Это вложенный генератор — возвращаемся к предыдущему
                self.sendval = None
                self.target = self.stack.pop()
```

### 3. Минимальный пример работы

Небольшой сценарий с `double`, `add` и `main` показывает, как `Task` обрабатывает вложенные генераторы и передаёт результат обратно в вызывающую корутину.

```python run session=scheduler
def double(x):
    yield x * x


def add(x, y):
    yield from double(x + y)


def main():
    result = yield add(1, 2)
    print(result)  # 9
    yield


task = Task(main())
task.run()
```

### 4. Планировщик событий (Scheduler)

`Scheduler` управляет жизненным циклом задач и использует `selectors` для неблокирующего ввода-вывода.

Ключевые части:

- `ready` — очередь задач, готовых к исполнению;
- `task_map` — активные задачи по `tid`;
- `wait_for_read` / `wait_for_write` — регистрация ожидания файловых дескрипторов;
- `io_poll` и `io_task` — опрос событий ОС и возврат готовых задач в очередь;
- `_run_once` / `event_loop` — основной цикл кооперативного исполнения.

::: warning Код ниже запускайте локально
Дальше планировщик работает с сокетами, а в браузере сетевых сокетов нет.
:::

```python
import logging
from typing import Generator, Union
from queue import Queue
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE


# Логгер для вывода информации о завершении задач
logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        # Очередь задач, готовых к выполнению (FIFO)
        self.ready = Queue()
        # Селектор для отслеживания событий ввода-вывода
        self.selector = DefaultSelector()
        # Словарь активных задач {tid: Task}
        self.task_map = {}

    def add_task(self, coroutine: Generator) -> int:
        # Создаём объект Task из генератора
        new_task = Task(coroutine)
        # Сохраняем задачу в словаре активных задач
        self.task_map[new_task.tid] = new_task
        # Добавляем задачу в очередь выполнения
        self.schedule(new_task)
        return new_task.tid

    def exit(self, task: Task):
        logger.info('Task %d terminated', task.tid)
        # Удаляем задачу из активных
        del self.task_map[task.tid]

    # ===== Ожидание событий ввода-вывода =====

    def wait_for_read(self, task: Task, fd: int):
        # Проверяем, зарегистрирован ли уже этот файловый дескриптор
        try:
            key = self.selector.get_key(fd)
        # Если не зарегистрирован — регистрируем его на чтение
        except KeyError:
            self.selector.register(fd, EVENT_READ, (task, None))
        # Если уже зарегистрирован — добавляем событие чтения к существующим
        else:
            mask, (reader, writer) = key.events, key.data
            self.selector.modify(fd, mask | EVENT_READ, (task, writer))

    def wait_for_write(self, task: Task, fd: int):
        # Проверяем, зарегистрирован ли fd
        try:
            key = self.selector.get_key(fd)
        # Если нет — регистрируем на запись
        except KeyError:
            self.selector.register(fd, EVENT_WRITE, (None, task))
        # Если есть — добавляем событие записи
        else:
            mask, (reader, writer) = key.events, key.data
            self.selector.modify(fd, mask | EVENT_WRITE, (reader, task))

    # ===== Удаление событий =====

    def _remove_reader(self, fd: int):
        try:
            key = self.selector.get_key(fd)
        except KeyError:
            pass
        else:
            mask, (reader, writer) = key.events, key.data
            # Убираем флаг чтения
            mask &= ~EVENT_READ
            # Если событий больше нет — полностью удаляем fd
            if not mask:
                self.selector.unregister(fd)
            else:
                self.selector.modify(fd, mask, (None, writer))

    def _remove_writer(self, fd: int):
        try:
            key = self.selector.get_key(fd)
        except KeyError:
            pass
        else:
            mask, (reader, writer) = key.events, key.data
            # Убираем флаг записи
            mask &= ~EVENT_WRITE
            # Если событий не осталось — удаляем
            if not mask:
                self.selector.unregister(fd)
            else:
                self.selector.modify(fd, mask, (reader, None))

    # ===== Опрос ввода-вывода =====

    def io_poll(self, timeout: Union[None, float]):
        # Ждём события от ОС
        events = self.selector.select(timeout)
        for key, mask in events:
            fileobj, (reader, writer) = key.fileobj, key.data
            # Если fd готов к чтению — планируем задачу
            if mask & EVENT_READ and reader is not None:
                self.schedule(reader)
                self._remove_reader(fileobj)
            # Если fd готов к записи — планируем задачу
            if mask & EVENT_WRITE and writer is not None:
                self.schedule(writer)
                self._remove_writer(fileobj)

    # ===== Фоновая задача обработки ввода-вывода =====

    def io_task(self) -> Generator:
        while True:
            # Если нет обычных задач — ждём ввода-вывода блокирующе
            if self.ready.empty():
                self.io_poll(None)
            else:
                # Если задачи есть — не блокируемся
                self.io_poll(0)
            # Передаём управление планировщику
            yield

    # ===== Планирование задач =====

    def schedule(self, task: Task):
        self.ready.put(task)

    def _run_once(self):
        # Берём следующую задачу
        task = self.ready.get()
        try:
            # Выполняем задачу до следующей приостановки (yield)
            result = task.run()
            # Задача приостановилась и вернула SystemCall — обрабатываем его
            if isinstance(result, SystemCall):
                result.handle(self, task)
                return
        except StopIteration:
            # Задача завершилась — удаляем её
            self.exit(task)
            return
        # Задача ещё активна — возвращаем её в очередь
        self.schedule(task)

    # ===== Главный цикл =====

    def event_loop(self):
        # Добавляем фоновую задачу обработки ввода-вывода
        self.add_task(self.io_task())
        # Пока есть активные задачи — продолжаем выполнение
        while self.task_map:
            self._run_once()
```

### 5. Неблокирующие операции сокета

`ReadWait` и `WriteWait` — системные вызовы, которые приостанавливают текущую задачу до готовности сокета к чтению или записи.

`AsyncSocket` — тонкая обёртка над обычным `socket`, где `accept`, `recv` и `send` реализованы как корутины: перед настоящим системным вызовом они отдают управление планировщику через `yield ReadWait(...)` или `yield WriteWait(...)`.

```python
from socket import socket
from typing import Tuple


class WriteWait(SystemCall):
    """Системный вызов для ожидания готовности к записи на файловом дескрипторе."""

    def __init__(self, f):
        # Объект, который должен стать готовым к записи (обычно сокет)
        self.f = f

    def handle(self, sched, task):
        fd = self.f.fileno()
        # Регистрируем задачу на ожидание готовности к записи на этом дескрипторе
        sched.wait_for_write(task, fd)


class ReadWait(SystemCall):
    """Системный вызов для ожидания готовности к чтению на файловом дескрипторе."""

    def __init__(self, f):
        # Объект, который должен стать готовым к чтению (обычно сокет)
        self.f = f

    def handle(self, sched, task):
        fd = self.f.fileno()
        # Регистрируем задачу на ожидание готовности к чтению на этом дескрипторе
        sched.wait_for_read(task, fd)


class AsyncSocket:
    def __init__(self, sock: socket):
        # Оборачиваем обычный сокет
        self.sock = sock

    def accept(self) -> Tuple[AsyncSocket, Tuple[str, int]]:
        """Принимает новое соединение, дождавшись готовности сокета к чтению."""
        yield ReadWait(self.sock)
        client, addr = self.sock.accept()
        # Возвращаем асинхронный сокет для клиента и его адрес
        return AsyncSocket(client), addr

    def send(self, buffer: bytes):
        """Отправляет данные, дожидаясь готовности сокета к записи."""
        # Отправляем, пока в буфере есть данные
        while buffer:
            yield WriteWait(self.sock)
            sent = self.sock.send(buffer)
            # Удаляем отправленные данные из буфера
            buffer = buffer[sent:]

    def recv(self, maxbytes: int) -> bytes:
        """Получает данные, дождавшись готовности сокета к чтению."""
        yield ReadWait(self.sock)
        return self.sock.recv(maxbytes)

    def close(self):
        yield self.sock.close()
```

### 6. Echo-сервер поверх собственного цикла событий

Финальный блок собирает все части вместе:

- `server(port)` принимает новые подключения;
- для каждого клиента создаётся отдельная задача `handle_client`;
- `handle_client` читает данные и отправляет их обратно (echo);
- `shed.event_loop()` запускает бесконечный цикл обработки задач и событий ввода-вывода.

```python
import logging
import sys
from socket import socket, AF_INET, SOCK_STREAM

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


def handle_client(client, addr):
    print('Connection from', addr)
    # Читаем данные и отправляем их обратно, пока клиент не закроет соединение
    while True:
        data = yield from client.recv(65536)
        # Данных нет — клиент закрыл соединение
        if not data:
            break
        yield from client.send(data)
    print('Client closed')
    client.close()


def server(port):
    print('Server starting')
    # Обычный сокет: привязываем к порту и начинаем слушать входящие соединения
    rawsock = socket(AF_INET, SOCK_STREAM)
    rawsock.bind(('', port))
    rawsock.listen()
    # Оборачиваем в асинхронный, чтобы использовать с планировщиком
    sock = AsyncSocket(rawsock)
    try:
        while True:
            # Ждём нового соединения
            client, addr = yield from sock.accept()
            # Для каждого клиента — отдельная задача
            yield NewTask(handle_client(client, addr))
    finally:
        sock.close()


if __name__ == '__main__':
    shed = Scheduler()
    shed.add_task(server(8000))

    try:
        shed.event_loop()
    except KeyboardInterrupt:
        print('\nСервер остановлен пользователем')
```

Проверка: подключитесь к серверу командой `nc localhost 8000` и отправьте строку — она вернётся обратно. Вывод сервера:

```text
Server starting
Connection from ('127.0.0.1', 57776)
Client closed
Task 4 terminated

Сервер остановлен пользователем
```

## Частые ошибки

- Задача крутит долгий цикл без `yield` → планировщик не получает управление, остальные задачи и опрос сокетов стоят → отдавать управление на каждой итерации или ждать событие через `ReadWait`/`WriteWait`.
- Вложенную корутину вызвали как обычную функцию (`client.recv(1024)` вместо `yield from client.recv(1024)`) → получили объект-генератор вместо данных, код внутри не выполнился → вызывать вложенные генераторы через `yield from` или отдавать их через `yield`, чтобы `Task.run()` положил их на стек.
- Селектор опрашивают с таймаутом `None`, когда в очереди `ready` есть задачи → планировщик блокируется на `select()`, и готовые задачи ждут первого сетевого события → при непустой очереди опрашивать с таймаутом `0`, как делает `io_task`.
- Сокет не снят с регистрации перед закрытием → `select()` возвращает событие на закрытом дескрипторе, при следующем опросе `ValueError` или `OSError` → снимать дескриптор через `_remove_reader`/`_remove_writer` до `close()`.
- Планировщик запущен без фоновой задачи `io_task` → `_run_once` крутит только обычные задачи, и `accept` никогда не дождётся подключения → запускать цикл через `event_loop()`, который регистрирует задачу ввода-вывода сам.

## Когда не использовать

Самодельный планировщик — учебная модель, а не замена `asyncio`. В рабочем коде берите `asyncio`: у него есть таймеры, отмена задач, обработка исключений, TLS и готовые протоколы, а корутины на генераторах давно заменены на `async`/`await`.

Если задача — один сервер на несколько клиентов без корутин вообще, хватит и модуля `selectors` напрямую, как в заметке [Сокеты](sockets.md).

## Связанные темы

- [Многозадачность в Python](README.md)
- [Асинхронность (asyncio)](async.md)
- [Сокеты](sockets.md)
- [Цикл событий asyncio наглядно](event_loop_visual.md)
