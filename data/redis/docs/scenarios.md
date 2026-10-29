# Redis: пять типовых сценариев

Чаще всего Redis используют не как «ещё одну базу», а для конкретных небольших задач. Ниже пять самых частых. Каждый пример — рабочий код на `redis-py`, его можно запустить на локальном Redis.

```python
import json
import time
import uuid

import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
```

## 1. Кэш медленных данных

Задача читается из базы 0,5 секунды: тяжёлый запрос или внешний сервис. Её часто открывают, а меняют редко.

**Идея (cache-aside):** сначала смотрим в Redis. Если там пусто — читаем из базы и кладём результат в Redis со сроком жизни.

```python
def load_task_from_db(task_id):
    time.sleep(0.5)
    return {'id': task_id, 'title': 'Сдать отчёт'}


def get_task(task_id):
    key = f'task:{task_id}'
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached)

    task = load_task_from_db(task_id)
    r.set(key, json.dumps(task, ensure_ascii=False), ex=300)
    return task


get_task(42)  # 0.510 с — из базы
get_task(42)  # 0.001 с — из кэша
```

Когда задача меняется, кэш нужно сбросить, иначе пользователи 5 минут будут видеть старые данные:

```python
def update_task_title(task_id, title):
    ...  # сохраняем в базу
    r.delete(f'task:{task_id}')
```

Так устроена статистика задач в [«Задачнике»](fastapi.md).

## 2. Счётчики просмотров

**Идея:** `INCR` атомарен, поэтому счётчик не теряет просмотры при одновременных запросах. А для количества **уникальных** посетителей есть `HyperLogLog`: он занимает около 12 КБ на ключ, сколько бы посетителей ни было, а ошибается меньше чем на 1%.

```python
for user in ['anna', 'boris', 'anna', 'anna']:
    r.incr('views:task:42')
    r.pfadd('visitors:task:42', user)

r.get('views:task:42')       # '4' — всего просмотров
r.pfcount('visitors:task:42')  # 2 — уникальных посетителей
```

Если нужен точный список посетителей, используйте множество (`SADD`, `SCARD`), но памяти уйдёт больше.

## 3. Ограничение частоты запросов (rate limiting)

Не больше 5 попыток входа в минуту с одного адреса — защита от перебора паролей.

**Идея (фиксированное окно):** ключ включает номер текущей минуты. `INCR` считает запросы, а `EXPIRE ... NX` ставит срок жизни, если его ещё нет, чтобы счётчик исчез сам. Обе команды уходят одним `pipeline`, то есть одной транзакцией.

```python
def allow_request(user_id, limit=5, window=60):
    key = f'rate:{user_id}:{int(time.time() // window)}'
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)  # NX — только если срок ещё не задан (Redis 7+)
    count, _ = pipe.execute()
    return count <= limit


[allow_request('anna') for _ in range(7)]
# [True, True, True, True, True, False, False]
```

У фиксированного окна есть недостаток: на стыке минут можно сделать 5 запросов в 12:00:59 и ещё 5 в 12:01:00. Если это важно, используют «скользящее окно» на упорядоченном множестве. Для защиты входа обычно хватает фиксированного.

## 4. Распределённая блокировка

Ежедневный отчёт строят три копии сервиса, а нужно, чтобы строила одна.

**Идея:** `SET ключ значение NX EX 30` записывает ключ, только если его ещё нет. Это атомарно, поэтому ключ получит ровно один воркер. Срок жизни защищает от вечной блокировки, если воркер упал.

```python
def acquire(name, ttl=30):
    token = str(uuid.uuid4())
    if r.set(f'lock:{name}', token, nx=True, ex=ttl):
        return token
    return None


acquire('daily-report')  # 'c0b1...' — блокировка получена
acquire('daily-report')  # None — уже занято
```

Снимать блокировку нужно осторожно: если работа шла дольше 30 секунд, ключ мог истечь, и его уже взял другой воркер. Поэтому удаляем ключ только при совпадении токена. Проверку и удаление делаем одним Lua-скриптом, чтобы они были атомарны:

```python
RELEASE = r.register_script("""
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
""")


def release(name, token):
    return RELEASE(keys=[f'lock:{name}'], args=[token])


release('daily-report', 'чужой-токен')  # 0 — не наша блокировка, не трогаем
release('daily-report', token)          # 1 — сняли
```

В redis-py всё это уже есть готовым:

```python
with r.lock('lock:daily-report', timeout=30, blocking_timeout=1):
    build_report()
```

## 5. Очередь заданий

Сервис должен отправить письма, но не заставлять пользователя ждать.

**Идея:** производитель кладёт задания в список (`LPUSH`), а воркер забирает их с другого конца (`BRPOP`). `BRPOP` ждёт, пока задание появится, не нагружая Redis постоянными опросами.

```python
def producer():
    for i in range(3):
        r.lpush('queue:emails', json.dumps({'to': f'user{i}@example.com'}))


def consumer():
    while True:
        item = r.brpop('queue:emails', timeout=1)
        if item is None:
            break
        _, payload = item
        print('отправляем письмо', json.loads(payload)['to'])


producer()
consumer()
# отправляем письмо user0@example.com
# отправляем письмо user1@example.com
# отправляем письмо user2@example.com
```

Минус: если воркер упал, взяв задание, задание потеряно. Надёжные очереди строят на `Stream` с подтверждениями или берут готовый инструмент — [Celery](../../../framework/celery/README.md), [Dramatiq](../../../framework/dramatiq/README.md), [RabbitMQ](../../../microservices/broker/rabbitmq/README.md).

## Бонус: публикация событий

`PUBLISH` рассылает сообщение всем, кто сейчас подписан на канал:

```python
pubsub = r.pubsub()
pubsub.subscribe('tasks:events')

r.publish('tasks:events', 'task 42 done')  # 1 — число получателей
```

Сообщения не сохраняются: кто не был подписан в момент публикации, ничего не получит. Подходит для уведомлений «здесь и сейчас», например для обновления интерфейса через WebSocket.

## Частые ошибки

- **`INCR`, а потом `EXPIRE` отдельной командой.** Если процесс упадёт между ними, ключ останется без срока жизни навсегда. Для rate limiter это значит вечную блокировку пользователя. Отправляйте обе команды одним `pipeline`, как в примере.
- **Блокировка без срока жизни.** Воркер упал — блокировка висит вечно.
- **`DEL` чужой блокировки.** Снимайте только по своему токену.
- **Pub/Sub как очередь.** Сообщения теряются, если получатель был отключён.

## Связанные темы

- [Основы Redis](basics.md)
- [Redis в FastAPI](fastapi.md)
- [Потерянные обновления в PostgreSQL](../../postgres/docs/tasks.md) — та же проблема гонки в SQL
