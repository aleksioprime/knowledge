# Ограничение частоты запросов

В «Задачник» кто-то перебирает пароли: сотни попыток входа в минуту. Мобильное приложение после неудачного релиза опрашивает `/tasks` каждые 10 мс вместо 10 секунд. Партнёр выгружает данные циклом без пауз — и база тормозит для всех остальных. Ограничение частоты (rate limiting) отвечает на вопрос «сколько запросов разрешено этому клиенту за это время» и лишнее отклоняет сразу, не доводя до базы.

Есть и обратная сторона: SMS-шлюз, через который «Задачник» шлёт коды входа, принимает не больше 5 запросов в секунду и за превышение отвечает 429 или блокирует ключ. Здесь лимит нужен уже нам — на **исходящие** запросы.

Примеры проверены на Python 3.12, redis-py 8.1.0, Redis 8.8.4 и FastAPI 0.162 на Apple M1.

## Минимальный пример: корзина с токенами

Не больше 10 запросов в минуту на пользователя, но разрешить короткий всплеск:

```python
class TokenBucket:
    def __init__(self, capacity: int, rate: float):
        self.capacity, self.rate = capacity, rate  # rate — токенов в секунду
        self.tokens, self.updated = float(capacity), 0.0

    def allow(self, now: float) -> bool:
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


bucket = TokenBucket(capacity=10, rate=10 / 60)
[bucket.allow(now=0.0) for _ in range(12)]  # 10 × True, затем False, False
bucket.allow(now=6.0)                       # True — за 6 секунд накопился один токен
```

Время передаётся параметром, чтобы пример был воспроизводимым; в сервисе это `time.monotonic()`. Дальше — какие ещё бывают алгоритмы, как сделать такой лимит общим для нескольких копий сервиса и что отвечать клиенту.

## Как это работает

### Алгоритмы

Сравнивать будем на одном сценарии: лимит 5 запросов в секунду, клиент шлёт пачки по 5 запросов в моменты 0,9 с, 1,0 с, 1,5 с и 3,0 с. Код всех вариантов — ниже, результат такой:

```text
                t=0.9  t=1.0  t=1.5  t=3.0
fixed window    5/5    5/5    0/5    5/5
sliding log     5/5    0/5    0/5    5/5
sliding counter 5/5    1/5    2/5    5/5
token bucket    5/5    0/5    3/5    5/5
```

#### Фиксированное окно (fixed window)

Счётчик на каждую секунду (минуту, час): ключ — номер окна, при смене окна счётчик начинается с нуля. Версия на Redis с `INCR` и `EXPIRE` разобрана в заметке [Redis: типовые сценарии](../databases/redis/scenarios.md#3-ограничение-частоты-запросов-rate-limiting), здесь — та же логика в памяти:

```python
class FixedWindow:
    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.current_window, self.count = -1, 0

    def allow(self, now: float) -> bool:
        window_id = math.floor(now / self.window)
        if window_id != self.current_window:
            self.current_window, self.count = window_id, 0
        if self.count < self.limit:
            self.count += 1
            return True
        return False
```

Самый простой и дешёвый: одно число на клиента. Недостаток виден в таблице: 5 запросов в 0,9 с и ещё 5 в 1,0 с — **10 запросов за 0,1 секунды** при лимите 5 в секунду. На стыке окон пропускается вдвое больше лимита.

#### Скользящий журнал (sliding log)

Храним время каждого запроса и считаем, сколько из них попало в последнюю секунду:

```python
class SlidingLog:
    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.log: deque[float] = deque()

    def allow(self, now: float) -> bool:
        while self.log and self.log[0] <= now - self.window:
            self.log.popleft()
        if len(self.log) < self.limit:
            self.log.append(now)
            return True
        return False
```

Точный: за любую секунду — не больше лимита. Но память пропорциональна лимиту: при лимите 1000 запросов в час на каждого клиента хранится до 1000 отметок. На Redis делается на упорядоченном множестве (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`).

#### Скользящее окно со счётчиками (sliding window counter)

Компромисс: два счётчика — текущего и предыдущего окна. Предыдущее окно учитывается с весом той доли, которая ещё попадает в последнюю секунду:

```python
class SlidingWindowCounter:
    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.current_window, self.current, self.previous = 0, 0, 0

    def allow(self, now: float) -> bool:
        window_id = math.floor(now / self.window)
        if window_id != self.current_window:
            # окно сдвинулось: текущий счётчик стал предыдущим (или обнулился, если прошло больше окна)
            self.previous = self.current if window_id == self.current_window + 1 else 0
            self.current_window, self.current = window_id, 0
        elapsed = now / self.window - window_id  # доля текущего окна, которая уже прошла
        estimated = self.previous * (1 - elapsed) + self.current
        if estimated < self.limit:
            self.current += 1
            return True
        return False
```

Два числа на клиента и почти точный результат. «Почти» видно в таблице: в момент 1,0 с пропущен один запрос, хотя за последнюю секунду их уже было 5. Алгоритм предполагает, что запросы прошлого окна шли равномерно, а они пришли пачкой в конце. На практике ошибка небольшая; такой подход, например, описывал Cloudflare для своих лимитов.

#### Корзина с токенами (token bucket)

Код — в минимальном примере. В корзину с постоянной скоростью капают токены, но не больше её ёмкости; каждый запрос забирает токен; нет токена — отказ.

Два параметра вместо одного: **скорость** (`rate`) задаёт среднюю частоту, **ёмкость** (`capacity`) — размер допустимого всплеска. Клиент, который молчал минуту, может сразу сделать 10 запросов, а дальше — не чаще одного в 6 секунд. Это хорошо ложится на реальное поведение: пользователь открыл приложение — пачка запросов, потом тишина. Хранится тоже два числа: токены и время последнего обновления. Этот алгоритм описывают в документации к своим лимитам, например, AWS API Gateway и Stripe.

#### Дырявое ведро (leaky bucket)

Запросы встают в очередь, а выходят из неё с постоянной скоростью, как вода из ведра с дыркой. Переполнилось ведро — новые запросы отклоняются. В отличие от остальных алгоритмов, лишний запрос не отклоняется сразу, а **ждёт** — поток на выходе получается ровным:

```python
class LeakyBucket:
    """Очередь с постоянной скоростью выхода: возвращает, сколько ждать, или None, если очередь полна."""

    def __init__(self, rate: float, queue_size: int):
        self.interval, self.queue_size = 1 / rate, queue_size
        self.next_free = 0.0

    def acquire(self, now: float) -> float | None:
        start = max(now, self.next_free)
        wait = start - now
        if wait >= self.queue_size * self.interval:
            return None
        self.next_free = start + self.interval
        return wait
```

Тот же сценарий, скорость 5 в секунду, очередь на 5 мест — для каждого запроса задержка или отказ:

```text
t=0.9:  ['+0.00', '+0.20', '+0.40', '+0.60', '+0.80']
t=1.0:  ['+0.90', 'отказ', 'отказ', 'отказ', 'отказ']
t=1.5:  ['+0.60', '+0.80', '+1.00', 'отказ', 'отказ']
t=3.0:  ['+0.00', '+0.20', '+0.40', '+0.60', '+0.80']
```

Пачка из пяти превратилась в запросы через каждые 0,2 с. Это то, что нужно, когда защищаемая сторона не выносит всплесков: старая база, чужой API со строгим лимитом. Цена — задержка ответа и место под очередь.

#### Сравнение

| Алгоритм | Память на клиента | Точность | Всплески | Когда брать |
|---|---|---|---|---|
| Фиксированное окно | 1 счётчик | до 2× лимита на стыке окон | пропускает на стыке | грубая защита, лимиты «в сутки» |
| Скользящий журнал | все отметки за окно | точный | нет | маленькие лимиты, где важна точность (попытки входа) |
| Скользящее окно со счётчиками | 2 счётчика | приблизительный | сглажены | общий лимит на API |
| Корзина с токенами | 2 числа | точный по средней скорости | разрешены до ёмкости | API для людей и клиентов с пачками запросов |
| Дырявое ведро | очередь или 1 число | точный, ровный выход | превращаются в задержку | защита чувствительной зависимости, исходящие запросы |

### Распределённый лимит

#### Локальные счётчики не работают

Сервис запущен в трёх копиях за балансировщиком, у каждой своя корзина в памяти на 10 запросов:

```python
from itertools import cycle

instances = [TokenBucket(capacity=10, rate=10 / 60) for _ in range(3)]  # у каждой копии свой счётчик
balancer = cycle(instances)
sum(next(balancer).allow(now=0.0) for _ in range(50))  # 30
```

Пропущено 30 вместо 10: при N копиях лимит фактически становится N × лимит, и меняется при каждом масштабировании.

**Липкие сессии** (sticky sessions) — балансировщик всегда отправляет клиента на одну и ту же копию — формально решают задачу, но ломают то, ради чего копий несколько: нагрузка распределяется неравномерно, при падении копии её клиенты получают свежий лимит, а сервис перестаёт быть [без состояния](scaling.md#приложение-без-состояния-stateless).

Остаются два варианта: считать там, где весь трафик проходит через одну точку, или хранить счётчики в общем хранилище.

#### Лимит на балансировщике

nginx перед сервисом видит все запросы. Его `limit_req` — это дырявое ведро: `rate` — скорость выхода, `burst` — размер очереди. Без `nodelay` запросы сверх скорости ждут в очереди, как в примере выше; с `nodelay` очередь пропускается сразу, а `burst` работает как ёмкость корзины с токенами. Настройка — в заметке [Ограничения и безопасность NGINX](../web/nginx/security.md#ограничение-частоты), пример лимита на шлюзе Traefik — в [API Gateway](../microservices/api_gateway/README.md#ограничение-частоты-запросов).

Плюсы: лишние запросы не доходят до Python вообще, настройка в одном месте. Минусы: nginx знает только IP, заголовки и путь — лимит «по тарифу пользователя» или «по числу созданных задач» на нём не сделать. И если nginx сам запущен в нескольких копиях, у каждой свой счётчик — та же проблема на уровень выше.

#### Общий Redis и Lua-скрипт

Счётчики в Redis видны всем копиям. Но корзина с токенами — это «прочитать → посчитать → записать», и если делать это тремя командами из Python, параллельные запросы прочитают одно и то же значение. Скрипт на Lua Redis выполняет целиком, не прерываясь на другие команды, — гонки нет:

```python
TOKEN_BUCKET = """
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])              -- токенов в секунду
local t = redis.call('TIME')                -- время сервера Redis, а не инстанса приложения
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

local state = redis.call('HMGET', KEYS[1], 'tokens', 'updated')
local tokens = tonumber(state[1]) or capacity
local updated = tonumber(state[2]) or now
tokens = math.min(capacity, tokens + (now - updated) * rate)

local allowed = 0
local retry_after = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
else
    retry_after = (1 - tokens) / rate
end

redis.call('HSET', KEYS[1], 'tokens', tokens, 'updated', now)
redis.call('PEXPIRE', KEYS[1], math.ceil(capacity / rate * 1000))
-- дробные числа Redis обрезал бы до целых, поэтому отдаём строками
return {allowed, tostring(tokens), tostring(retry_after)}
"""


@dataclass
class Decision:
    allowed: bool
    remaining: int
    retry_after: float


class RedisTokenBucket:
    def __init__(self, client: redis.Redis, capacity: int, rate: float):
        self.capacity, self.rate = capacity, rate
        self.script = client.register_script(TOKEN_BUCKET)

    async def hit(self, key: str) -> Decision:
        allowed, tokens, retry_after = await self.script(keys=[f'rl:{key}'], args=[self.capacity, self.rate])
        return Decision(bool(allowed), int(float(tokens)), float(retry_after))
```

- время берётся из Redis (`TIME`): у копий сервиса часы могут расходиться, а у Redis они одни;
- `PEXPIRE` — ключ исчезает, когда корзина гарантированно снова полна, и Redis не копит ключи ушедших клиентов;
- `register_script` отправляет скрипт один раз и дальше вызывает его по SHA-хэшу (`EVALSHA`).

Проверка гонки: 50 одновременных запросов через `asyncio.gather` при лимите 10 в минуту. Для сравнения — та же логика тремя отдельными командами (`TIME`, `HMGET`, `HSET`) из Python:

```python
client = redis.Redis(port=36379, decode_responses=True, max_connections=100)
bucket = RedisTokenBucket(client, capacity=10, rate=10 / 60)

decisions = await asyncio.gather(*(bucket.hit('anna') for _ in range(50)))
results = await asyncio.gather(*(naive_hit(client, 'boris', 10, 10 / 60) for _ in range(50)))
```

```text
Lua: пропущено 10 из 50
последний отказ: Decision(allowed=False, remaining=0, retry_after=5.9510300159454)
без Lua: пропущено 50 из 50
```

Три прогона подряд — одинаковый результат. Без скрипта все 50 запросов прочитали полную корзину раньше, чем кто-то из них успел записать уменьшенную. Вместо Lua можно использовать `WATCH`/`MULTI` с повтором при конфликте, но под нагрузкой на один ключ это много повторов; скрипт проще.

Готовые библиотеки: `limits` (фиксированное и скользящее окно, бэкенды Redis и Memcached) и построенные на ней `slowapi` для FastAPI и Starlette.

### Ответ клиенту: 429 и заголовки

Отказ — это код **429 Too Many Requests** и заголовок **`Retry-After`** — через сколько секунд стоит повторить. Хороший клиент по нему ждёт, а не долбит сервер в цикле. Дополнительно сообщают состояние лимита и в успешных ответах, чтобы клиент мог притормозить заранее:

```python
CAPACITY, RATE = 10, 10 / 60
bucket = RedisTokenBucket(client, capacity=CAPACITY, rate=RATE)


def client_key(request: Request) -> str:
    user_id = request.headers.get('X-User-Id')  # в реальном сервисе — из проверенного токена
    return f'user:{user_id}' if user_id else f'ip:{request.client.host}'


@app.middleware('http')
async def rate_limit(request: Request, call_next):
    try:
        decision = await bucket.hit(client_key(request))
    except redis.RedisError as error:
        logger.warning('лимит не проверен, пропускаем запрос: %r', error)  # fail-open
        return await call_next(request)

    headers = {'RateLimit-Limit': str(CAPACITY), 'RateLimit-Remaining': str(decision.remaining)}
    if not decision.allowed:
        retry_after = str(math.ceil(decision.retry_after))
        headers |= {'Retry-After': retry_after, 'RateLimit-Reset': retry_after}
        return JSONResponse({'detail': 'слишком много запросов'}, status_code=429, headers=headers)
    response = await call_next(request)
    response.headers.update(headers)
    return response
```

13 запросов Анны и один Бориса:

```text
[200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429]
429 {'ratelimit-limit': '10', 'ratelimit-remaining': '0', 'retry-after': '6', 'ratelimit-reset': '6'}
boris: 200 9
```

`Retry-After` и 429 — стандарт HTTP. С заголовками состояния единства нет: многие API пишут `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`; черновик IETF «RateLimit header fields» в ранних версиях предлагал те же три заголовка без `X-`, в поздних — два структурированных, `RateLimit` и `RateLimit-Policy`. Выберите один вариант и опишите его в документации API.

### По какому ключу считать

- **пользователь** (id из проверенного токена) — справедливо: один клиент не съедает лимит другого. Основной вариант для авторизованных запросов;
- **IP** — для анонимных запросов: вход, регистрация, восстановление пароля. Но за одним IP бывает целый офис или мобильный оператор (NAT), а атакующий легко меняет адреса. За балансировщиком сначала настройте настоящий IP клиента, иначе все запросы придут «с балансировщика»;
- **ключ API или клиентское приложение** — лимит по тарифу партнёра;
- **эндпоинт** — у дорогих операций свой, более строгий лимит: экспорт задач в CSV — раз в минуту, чтение списка — сотни раз.

Ключи комбинируют: `login:ip:203.0.113.5` и `login:email:anna@example.com` — перебор паролей с разных адресов к одному аккаунту тоже упрётся в лимит. Лимит по логину лучше считать только по неудачным попыткам, иначе злоумышленник заблокирует вход настоящему пользователю.

### Если Redis недоступен

Хранилище лимитов — ещё одна зависимость, которая может упасть. Решать заранее:

- **fail-open** (пропускать) — лимит временно не работает, но сервис работает. Подходит для общего лимита на API: лучше на несколько минут остаться без защиты от болтливых клиентов, чем отказать всем;
- **fail-closed** (отказывать) — когда лимит защищает от реального вреда: попытки входа, отправка SMS за наш счёт, платёжные операции.

Тот же middleware, направленный на порт, где Redis нет:

```text
WARNING лимит не проверен, пропускаем запрос: network:ConnectionError
...
[200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200]
```

Обязательны короткие таймауты клиента Redis (`socket_connect_timeout=0.2`, `socket_timeout=0.2`), иначе каждая проверка лимита будет ждать недоступный Redis секундами. Чтобы не стучаться в лежащий Redis на каждом запросе, проверку оборачивают в [circuit breaker](resilience.md#минимальный-пример-circuit-breaker), а сбой выводят в метрику и алерт.

### Исходящий лимит

SMS-шлюз разрешает 5 запросов в секунду. Частая ошибка — ограничить запросы семафором:

```python
semaphore = asyncio.Semaphore(5)


async def with_semaphore(phone: str) -> None:
    async with semaphore:
        await send_sms(phone)  # внешний API отвечает за 100 мс
```

Семафор ограничивает число **одновременных** запросов, а не их частоту. Если ответ приходит за 100 мс, пять «слотов» освобождаются 10 раз в секунду, и получается 50 запросов в секунду. Для частоты нужен лимитер — здесь дырявое ведро, которое назначает каждому вызову свой момент старта:

```python
class AsyncRateLimiter:
    """Не чаще rate запросов в секунду: каждый вызов получает свой момент старта."""

    def __init__(self, rate: float):
        self.interval = 1 / rate
        self.next_slot = 0.0
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        async with self.lock:
            now = time.monotonic()
            start = max(now, self.next_slot)
            self.next_slot = start + self.interval
        await asyncio.sleep(start - now)

    async def __aexit__(self, *exc):
        return False


limiter = AsyncRateLimiter(rate=5)


async def with_limiter(phone: str) -> None:
    async with limiter:
        await send_sms(phone)
```

20 SMS, «в пике» — максимум запросов, начатых за любую секунду:

```text
Semaphore(5): 20 запросов за 0.41 с, в пике 20 в секунду
RateLimiter(5/с): 20 запросов за 3.90 с, в пике 6 в секунду
```

С семафором шлюз получил бы в четыре раза больше разрешённого. С лимитером — ровно по запросу каждые 0,2 с; «6 в пике» — это первый и шестой запрос, которые разделяют ровно 1,0 с плюс-минус точность таймера. Если внешний API считает строго по скользящему окну, шестой запрос может оказаться лишним, поэтому лимит ставят с запасом: 4,5 в секунду вместо 5.

На практике нужны оба: семафор — чтобы не открыть сотню соединений сразу, лимитер — чтобы не превысить частоту. Готовая реализация — `aiolimiter` (`AsyncLimiter(5, 1)`). Если копий отправителя несколько, исходящий лимит тоже должен быть общим — тот же Lua-скрипт в Redis. А если внешний API всё же ответил 429, нужно подождать `Retry-After` и повторить — см. [повторы с паузой](resilience.md#повторы-с-паузой-и-разбросом).

## Частые ошибки

- **Лимит в памяти при нескольких копиях** — фактический лимит в N раз больше и меняется при масштабировании.
- **Чтение и запись счётчика разными командами** — гонка, под нагрузкой лимит не работает совсем (50 из 50 в примере выше). Нужен Lua-скрипт или атомарная команда (`INCR`).
- **Лимит по IP за балансировщиком без настройки real IP** — у всех пользователей один адрес и один общий лимит.
- **429 без `Retry-After`** — клиенты повторяют сразу и усиливают нагрузку.
- **Семафор вместо лимита частоты** для внешнего API.
- **Время приложения в распределённом лимите** — часы копий расходятся; берите время Redis.
- **Ключи без срока жизни** — Redis копит счётчики всех клиентов, которые когда-либо приходили.
- **Fail-closed без осознанного решения** — упал Redis, и вместе с ним весь API.

## Когда не использовать

Внутренний сервис, к которому ходят только свои сервисы с предсказуемой нагрузкой, обычно защищают не лимитом на клиента, а [таймаутами, выключателями и перегородками](resilience.md). Если нужно защитить сам сервис от перегрузки независимо от того, кто шлёт запросы, лучше работает ограничение одновременных запросов (очередь с ограниченной длиной и отказ 503), а не частоты. И лимит в приложении не заменяет защиту от DDoS: объёмную атаку отбивают на уровне сети и CDN, до вашего сервиса она доходить не должна.

## Связанные темы

- [Redis: фиксированное окно на INCR и EXPIRE](../databases/redis/scenarios.md#3-ограничение-частоты-запросов-rate-limiting)
- [NGINX: limit_req и limit_conn](../web/nginx/security.md#ограничение-частоты)
- [API Gateway: лимит на шлюзе](../microservices/api_gateway/README.md#ограничение-частоты-запросов)
- [Устойчивость: таймауты, повторы, circuit breaker](resilience.md)
- [Масштабирование: приложение без состояния](scaling.md#приложение-без-состояния-stateless)
