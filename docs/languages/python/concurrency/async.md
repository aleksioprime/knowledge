# Асинхронность в Python

Асинхронность нужна, когда программа в основном ждёт: ответа сервера, базы данных, файла. Вместо того чтобы простаивать в каждом ожидании, `asyncio` переключается между задачами в одном потоке — десять запросов по секунде занимают секунду, а не десять. В заметке собраны корутины, задачи, Future и функции `asyncio`, которые нужны на практике.

::: tip Примеры запускаются прямо на странице
Нажмите «Запустить» под блоком кода. Как и в Jupyter, корутину здесь можно ожидать через `await` на верхнем уровне. В обычном скрипте вместо этого пишут `asyncio.run(main())`.
:::

## Минимальный пример

Две «загрузки заказов» ждут одновременно, поэтому всё занимает 0,3 секунды, а не 0,4:

```python run
import asyncio


async def fetch_order(order_id, delay):
    await asyncio.sleep(delay)  # ждём ответ «сервера», не блокируя цикл
    return f'заказ {order_id} готов'


async def main():
    orders = await asyncio.gather(
        fetch_order(1, 0.3),
        fetch_order(2, 0.1),
    )
    print(orders)  # ['заказ 1 готов', 'заказ 2 готов']


await main()
```

## Как это работает

### Корутина

Корутина — функция, которая может приостановиться и потом продолжить работу с того же места.

```python run
import asyncio


# НЕПРАВИЛЬНО
async def example_coroutine():
    print('Hello from coroutine!')

example_coroutine()  # создан объект корутины, но сама корутина не запущена!


# ПРАВИЛЬНО
async def example_coroutine():
    print('Hello from coroutine!')

await example_coroutine()  # корутина запущена
```

### Task

Объект Task — обёртка над корутиной, которая позволяет выполнять несколько корутин конкурентно.

```python run
# Пример создания и запуска задачи
import asyncio


async def example_coroutine():
    await asyncio.sleep(1)
    print('Hello from coroutine!')


async def main():
    task = asyncio.create_task(example_coroutine())  # создаём задачу из корутины
    await task  # ждём выполнения задачи

await main()
```

```python run
# Пример создания и запуска нескольких задач
import asyncio


async def example_coroutine():
    await asyncio.sleep(1)
    print('Hello from coroutine!')


async def main():
    tasks = []
    for _ in range(10):
        task = asyncio.create_task(example_coroutine())  # создаём 10 задач
        tasks.append(task)
    await asyncio.gather(*tasks)  # ждём все задачи из списка: в сумме 1 секунда, а не 10

await main()
```

### Future

Future — результат асинхронной операции, который появится в будущем.

Объект Future или Task может находиться в одном из трёх состояний:

- Pending (ожидание) — операция, связанная с Future, ещё не выполнена.
- Completed (завершён) — операция завершена.
- Cancelled (отменён) — операция была отменена.

```python run
# Пример использования Future для получения результата из корутины
import asyncio


async def simulate_long_running_task(name, delay, future: asyncio.Future):
    print(f"Задача '{name}' началась, будет выполнена за {delay} секунд.")
    await asyncio.sleep(delay)
    result = f"Результат задачи '{name}'"
    print(f"Задача '{name}' завершена.")
    future.set_result(result)  # устанавливаем результат для Future


async def main():
    future = asyncio.Future()

    # Запускаем корутину, передаём в неё Future
    await simulate_long_running_task('Задача1', 3, future)

    # Получаем результат выполнения задачи
    result = future.result()
    print(f'Результат Future: {result}')

await main()
```

### Правила использования `await`

- `await` — ключевое слово, которое используется для переключения между awaitable-объектами.
- `await` нельзя использовать с объектами, которые не являются awaitable.
- `await` нельзя использовать вне корутин.
- `await` приостанавливает выполнение текущей корутины до получения результата.
- `await` возвращает результат.
- Корутина должна содержать `await`, иначе преимуществ asyncio не будет.

### Цикл событий

Цикл событий (event loop) работает в одном потоке и организует задачи: отмечает, когда какая задача должна начаться, и запускает её в нужный момент. Каждая корутина, запущенная в цикле событий, под капотом сообщает ему о своём статусе, чтобы он мог эффективно ею управлять. Когда в программе много асинхронных операций, цикл событий переключается между ними в оптимальном порядке.

Пошаговая анимация работы цикла — в заметке [Цикл событий asyncio наглядно](event_loop_visual.md).

![Цикл событий](img/event_loop.png)

Цикл событий обрабатывает события так:

- **Сбор событий.** Цикл отслеживает асинхронные события и задачи, которые нужно выполнить: операции ввода-вывода, таймеры, запланированные задачи. Они могут поступать из разных источников и добавляются в очередь на обработку.
- **Определение и распределение задач.** Когда событие готово к обработке, цикл определяет задачу или корутину, которая его обработает. Приоритеты обычно определяются автоматически.
- **Выполнение задач.** Цикл запускает задачу и управляет её выполнением. Асинхронная задача может приостановиться (`await`), чтобы дождаться других событий (например, ответа сервера), не блокируя цикл. Так цикл переключается между задачами и эффективно распределяет время процессора.
- **Ожидание и завершение событий.** Запустив задачу, цикл продолжает отслеживать другие события и возвращается к сбору событий, пока есть активные или ожидающие задачи.
- **Обработка ошибок.** Ошибку нужно обработать внутри задачи или через механизмы исключений asyncio. Необработанное исключение прерывает задачу, но не обязательно останавливает сам цикл.
- **Перезапуск цикла.** Цикл работает, пока его не остановят явно или пока не завершатся все задачи. Так приложение остаётся отзывчивым и обрабатывает события в реальном времени.

### Функции asyncio

#### asyncio.run()

`asyncio.run()` создаёт цикл событий и запускает в нём указанную корутину.

- `asyncio.run()` нельзя вызвать из корутины: функция не работает, когда в том же потоке уже запущен другой цикл событий.
- `asyncio.run()` принимает только корутины. Если передать обычную функцию, будет ошибка `ValueError`.
- Если в `main()` произошла ошибка, `asyncio.run(main())` отменит все остальные асинхронные операции и пробросит исключение в вызывающий код. Чтобы обработать исключение, добавьте `try`/`except` вокруг опасного участка.

#### asyncio.sleep()

`asyncio.sleep()` временно приостанавливает текущую корутину, позволяя циклу событий выполнять другие корутины и задачи.

Если нужно запустить задачи, добавленные в цикл, но не нужно ждать их результата, можно использовать `await asyncio.sleep(0)`. В этот момент произойдёт переключение контекста и начнут выполняться задачи. `await asyncio.sleep(0)` также можно ставить внутри корутин, чтобы дать возможность сменить контекст.

```python run
# await asyncio.sleep(0) переключает контекст после каждой итерации без ожидания,
# поэтому счётчики работают конкурентно
import asyncio


async def count():
    for i in range(3, 0, -1):
        print(f'Обратный отсчёт: {i}')
        await asyncio.sleep(0)


async def main():
    await asyncio.gather(count(), count())

await main()
```

#### asyncio.create_task()

`asyncio.create_task()` оборачивает корутину в объект Task, то есть планирует её выполнение в цикле событий.

После `asyncio.create_task(my_coroutine())` корутина оборачивается в Task и ставится в план. Выполняться задача начнёт при первом переключении контекста (`await`).

```python run
# Главная задача завершается, не дождавшись корутины: её вторая строка так и не напечатается
import asyncio


async def my_coroutine(seconds):
    print('Задача my_coroutine() запущена')
    await asyncio.sleep(seconds)
    print('Задача my_coroutine() завершена')


async def main():
    print('Задача main() запущена')
    task1 = asyncio.create_task(my_coroutine(3), name='TestTask')
    print('Задача main() завершена')
    # await task1  # если раскомментировать, main() дождётся завершения my_coroutine()

await main()
```

#### asyncio.ensure_future()

`asyncio.ensure_future()` — устаревший способ запустить корутину в асинхронном режиме. В новом коде используйте `asyncio.create_task()`.

```python run
import asyncio


async def my_coroutine(i):
    print(f'Начинается корутина {i}')
    await asyncio.sleep(1)
    print(f'Завершается корутина {i}')


async def main():
    tasks = [asyncio.ensure_future(my_coroutine(i)) for i in range(5)]
    await asyncio.gather(*tasks)

await main()
```

#### asyncio.gather()

`asyncio.gather()` группирует awaitable-объекты и выполняет их конкурентно. Если все ожидания завершились успешно, результатом будет список возвращаемых значений в том же порядке, в каком объекты переданы в `gather`.

Функция возвращает объект `asyncio.tasks._GatheringFuture` — особый Future, который собирает результаты переданных корутин. Если среди переданных объектов есть корутина, она автоматически оборачивается в Task.

```python run
# Пример использования asyncio.gather() для запуска нескольких корутин и получения их результатов
import asyncio
import time


async def coro(num):
    await asyncio.sleep(1 / num)
    return f'Задача_{num} была выполнена за {time.perf_counter() - start:.4f} секунды'


async def main():
    future = asyncio.gather(*[coro(i) for i in range(1, 6)])
    print(type(future))
    results = await future
    print(results)

start = time.perf_counter()
await main()
```

#### asyncio.wait_for()

`asyncio.wait_for(aw, timeout)` ждёт завершения awaitable-объекта. Если он не завершился за `timeout` секунд, объект отменяется и выбрасывается `TimeoutError`.

```python run
# Таймаут 3 секунды на корутину, которая работает 5 секунд
import asyncio


async def my_coro():
    await asyncio.sleep(5)
    return 'Привет мир!'


async def main():
    try:
        await asyncio.wait_for(my_coro(), timeout=3)
    except asyncio.TimeoutError:
        print('Корутина my_coro() не завершилась в течение 3 секунд и была прервана!')

await main()
```

#### asyncio.wait()

`asyncio.wait(aws, *, timeout=None, return_when=asyncio.ALL_COMPLETED)` конкурентно запускает задачи из `aws`. Она приостанавливает текущую корутину, пока не истечёт таймаут или не наступит условие из `return_when`. На другие корутины и основную программу это не влияет.

Функция возвращает два множества задач — `(done, pending)`:

- `done` — задачи, которые выполнены или отменены;
- `pending` — задачи, которые ещё не выполнены.

`return_when` принимает одну из констант:

- `FIRST_COMPLETED` — вернуть управление, как только любая задача будет выполнена или отменена;
- `FIRST_EXCEPTION` — вернуть управление, как только любая задача завершится с исключением;
- `ALL_COMPLETED` — значение по умолчанию: вернуть управление, когда все задачи выполнены или отменены.

По таймауту функция не выбрасывает `asyncio.TimeoutError`. Невыполненные задачи просто возвращаются во множестве `pending` и продолжают работать в фоне.

```python run
# Управление вернётся, когда завершатся все задачи или истечёт таймаут
import asyncio


async def my_coro(delay):
    """Асинхронная задача, которая просто ждёт указанное время."""
    task_name = asyncio.current_task().get_name()
    print(f'{task_name} началась, будет выполняться {delay} секунд(ы).')
    await asyncio.sleep(delay)
    print(f'{task_name} завершена.')
    return f'{task_name}: результат'


async def main():
    tasks = [asyncio.create_task(my_coro(i), name=f'Задача_{i}') for i in range(1, 4)]
    print('Запуск задач...')
    done, pending = await asyncio.wait(tasks, timeout=2.1)

    # Проверяем, какие задачи выполнены, а какие ещё в ожидании
    print(f'\nРезультаты завершённых задач: {[d.result() for d in done]}')
    if pending:
        print(f'Ожидающие задачи: {[x.get_name() for x in pending]}')
        # Оставшиеся задачи можно отменить, если это нужно
        print('Отмена задач...')
        for task in pending:
            print(f'{task.get_name()}: отмена')
            task.cancel()
    else:
        print('Все задачи завершены.')

await main()
```

#### asyncio.as_completed()

`asyncio.as_completed(aws, *, timeout=None)` выдаёт результаты задач по мере их завершения, а не в порядке запуска. Функция возвращает итератор, который отдаёт future по мере готовности.

```python run
# Обработка результатов задач по мере их завершения
import asyncio
import random


async def task(num):
    await asyncio.sleep(delay := random.random())
    return f'Task {num} completed, {delay=:.3f}'


async def main():
    tasks = [asyncio.create_task(task(i)) for i in range(5)]

    # as_completed() отдаёт задачи по мере завершения, поэтому результат можно обработать сразу после готовности
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        print(result)

await main()
```

### Собственный цикл событий

Документация asyncio в большинстве случаев рекомендует высокоуровневый `asyncio.run()`. Но для работы с некоторыми библиотеками и фреймворками понадобится создать цикл событий и обращаться к его методам:

- `loop = asyncio.new_event_loop()` — создание нового цикла событий;
- `asyncio.set_event_loop(loop)` — назначение созданного цикла текущим (в однопоточном приложении этот шаг необязателен);
- `loop.run_until_complete(coro())` — запуск корутины в созданном цикле;
- `loop.close()` — закрытие цикла по окончании работы.

Особенности:

- в одном приложении можно создать несколько разных циклов событий;
- в одном потоке в каждый момент может работать только один цикл;
- цикл событий надо закрывать вручную.

::: warning Эти примеры запускайте локально
В браузере уже работает цикл событий самой страницы, а потоков нет, поэтому `run_until_complete` и `threading` здесь недоступны.
:::

```python
import asyncio


async def main():
    print('Hello, World!')


loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)

loop.run_until_complete(main())
loop.close()
```

Каждому потоку — свой цикл событий:

```python
import asyncio
import threading


# Корутина, которая выполняется в каждом из независимых потоков
async def task(loop, num):
    # id потока, в котором выполняется задача
    thread_id = threading.current_thread().ident
    # Текущий цикл событий
    e_loop_id = asyncio.get_running_loop()
    print(
        f'Задача task_{num} запущена в потоке id: {thread_id}, '
        f'текущий event loop id: {id(e_loop_id)}, '
        f'переданный event loop id: {id(loop)}')
    await asyncio.sleep(num)
    print(f'Задача task_{num} завершена!')


# Запуск цикла событий в отдельном потоке
def start_loop(loop, coro, num):
    # Делаем переданный цикл текущим для этого потока
    asyncio.set_event_loop(loop)
    # Запускаем задачу в цикле и ждём её результата
    loop.run_until_complete(coro(loop, num))
    loop.close()


# Создаёт циклы событий и потоки
async def main():
    print(f'main()\nТекущий поток id: {threading.current_thread().ident}\n'
          f'Текущий цикл событий id: {id(asyncio.get_running_loop())}\n{"-" * 50}')
    loop1 = asyncio.new_event_loop()
    print(f'Создан новый цикл событий id: {id(loop1)}')
    loop2 = asyncio.new_event_loop()
    print(f'Создан новый цикл событий id: {id(loop2)}\n{"-" * 50}')

    # Каждому циклу событий — свой поток
    thread1 = threading.Thread(target=start_loop, args=(loop1, task, 1))
    thread2 = threading.Thread(target=start_loop, args=(loop2, task, 2))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()


asyncio.run(main())
```

## Частые ошибки

- Вызвали корутину без `await` → `RuntimeWarning: coroutine ... was never awaited`, код внутри не выполнился → добавить `await` или обернуть вызов в `asyncio.create_task()`.
- Блокирующий вызов внутри корутины (`time.sleep`, `requests.get`, тяжёлый расчёт) → весь цикл событий замирает, остальные задачи не двигаются → `await asyncio.sleep()`, асинхронный клиент (`aiohttp`, `httpx`) или `loop.run_in_executor()`.
- Создали задачу через `create_task()` и не сохранили ссылку → задача может исчезнуть при сборке мусора, а её ошибки теряются → хранить задачи в списке и дожидаться их через `gather()`.
- `asyncio.run()` внутри уже работающего цикла (Jupyter, браузер, обработчик фреймворка) → `RuntimeError: asyncio.run() cannot be called from a running event loop` → ожидать корутину через `await` или вынести запуск на верхний уровень скрипта.
- Исключение в одной из корутин `gather()` → остальные продолжают работать, но исключение всплывает при `await` и прерывает ожидание всего набора → передать `return_exceptions=True` или обрабатывать ошибки внутри каждой корутины.

## Когда не использовать

Асинхронность не ускоряет вычисления: если программа считает хэши, перемножает матрицы или обрабатывает изображения, цикл событий только добавит сложности, а GIL всё равно пустит к процессору один поток за раз. Для такой нагрузки нужны [процессы](multiprocessing.md).

Не стоит переводить на `asyncio` и простой скрипт с парой последовательных запросов: выигрыша по времени почти нет, а код становится «заразным» — каждая функция в цепочке вызовов должна стать корутиной. Если асинхронный код нужен только ради одной блокирующей библиотеки, проще вынести её вызов в [пул потоков](thread_pool.md).

## Связанные темы

- [Многозадачность в Python](README.md)
- [Цикл событий asyncio наглядно](event_loop_visual.md)
- [Event Loop своими руками](event_loop.md)
- [Пул потоков](thread_pool.md)
- [Потоки](multithreading.md)
- [Сокеты](sockets.md)
