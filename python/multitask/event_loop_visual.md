# Цикл событий asyncio наглядно

Асинхронный код ускоряет программу, только когда задачи много ждут: сеть, база, диск. Пока одна задача ждёт ответа, цикл событий (event loop) запускает другую. Если же задача блокирует поток, ускорения нет — и ждут все.

## Как цикл переключает задачи

Пройдите программу по шагам. Сначала посмотрите вкладку `await asyncio.sleep`, потом — `time.sleep`: код почти тот же, а время выполнения разное.

<EventLoopDemo />

Что видно на схеме:

- У цикла есть очередь готовых задач. Он берёт задачу и выполняет её до ближайшего `await`, который требует подождать.
- На `await` задача сама отдаёт управление (кооперативная многозадачность) и уходит в ожидание: таймер, ответ сокета, другая задача.
- Когда ожидание закончилось, задача возвращается в очередь и продолжает со следующей строки после `await`.
- Цикл работает в одном потоке. Всё, что выполняется без `await`, держит его целиком.

## Попробуйте сами

Код ниже выполняется прямо в браузере. Его можно изменить: поменяйте задержки или добавьте третью задачу.

```python run
import asyncio
import time


async def fetch(name, delay):
    print(f'{name}: запрос')
    await asyncio.sleep(delay)
    print(f'{name}: ответ через {delay} с')
    return name


async def main():
    started = time.perf_counter()
    results = await asyncio.gather(fetch('A', 2), fetch('B', 1))
    print(results)  # ['A', 'B'] — порядок как в gather, а не как завершились
    print(f'Всего: {time.perf_counter() - started:.1f} с')  # 2.0, а не 3.0


await main()
```

Теперь то же самое, но с блокирующей задержкой внутри корутины:

```python run
import asyncio
import time


async def fetch(name, delay):
    print(f'{name}: запрос')
    time.sleep(delay)  # блокирует поток вместе с циклом событий
    print(f'{name}: ответ через {delay} с')


async def main():
    started = time.perf_counter()
    await asyncio.gather(fetch('A', 2), fetch('B', 1))
    print(f'Всего: {time.perf_counter() - started:.1f} с')  # 3.0


await main()
```

::: tip Почему здесь `await main()`, а не `asyncio.run(main())`
В браузере цикл событий уже запущен — это цикл самой страницы. Поэтому корутину ожидают сразу через `await`. В обычном скрипте пишите `asyncio.run(main())`.
:::

## Задача, которая не отдаёт управление

Блокирует не только `time.sleep`. Любое долгое вычисление без `await` держит цикл. Пока считается сумма, «пульс» молчит:

```python run
import asyncio
import time


async def heartbeat():
    for _ in range(6):
        print(f'пульс {time.perf_counter() - started:.1f} с')
        await asyncio.sleep(0.5)


async def heavy():
    await asyncio.sleep(1)
    print('начинаю считать')
    total = sum(i * i for i in range(10_000_000))  # секунды без единого await
    print('посчитал')


started = time.perf_counter()
await asyncio.gather(heartbeat(), heavy())
```

Пульс должен идти каждые 0,5 с, но после «начинаю считать» он пропадает до конца вычисления.

## Частые ошибки

- `time.sleep`, `requests.get`, синхронный драйвер базы внутри `async def` → все остальные задачи и запросы замирают → используйте асинхронные аналоги (`asyncio.sleep`, `httpx.AsyncClient`, `asyncpg`) или вынесите вызов в поток через `await asyncio.to_thread(...)`.
- Корутину вызвали без `await` → код внутри не выполнился, а Python предупредил `coroutine ... was never awaited` → добавьте `await` или оберните в задачу `asyncio.create_task(...)`.
- Тяжёлые вычисления в корутине → цикл стоит, пока они идут → вынесите их в процесс: `loop.run_in_executor` с `ProcessPoolExecutor`.

## Когда не использовать

Если программа в основном считает (CPU-bound), asyncio не ускорит её: поток один, и считать параллельно он не умеет. Для вычислений нужны процессы — см. [Multiprocessing](multiprocessing.md).

## Связанные темы

- [Многозадачность в Python](README.md)
- [Асинхронность (asyncio)](async.md)
- [Event Loop своими руками](event_loop.md) — планировщик на генераторах и `selectors`
