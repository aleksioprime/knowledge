# Redis в FastAPI

Эндпоинт статистики каждый раз считает задачи пользователя тяжёлым запросом к PostgreSQL, а форму входа кто-то перебирает паролями без ограничений. Обе задачи решает Redis рядом с приложением: ответ запоминается на минуту, а попытки входа считаются по адресу. Здесь два сценария из [списка типовых](scenarios.md) на настоящем приложении — [«Задачнике»](../../../practice/projects/tasker/README.md):

- **кэш статистики** — эндпоинт `GET /tasks/stats` считает задачи пользователя и запоминает ответ на минуту;
- **ограничение попыток входа** — не больше 5 попыток в минуту с одного адреса, дальше ответ `429 Too Many Requests`.

## Минимальный пример

```bash
curl localhost:8000/tasks/stats -H "Authorization: Bearer $TOKEN"
# {"total":1,"done":0}

docker compose exec redis redis-cli GET stats:user:1
# "{\"total\":1,\"done\":0}"
docker compose exec redis redis-cli TTL stats:user:1
# (integer) 60
```

```bash
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w '%{http_code} ' -X POST localhost:8000/auth/token -d 'username=anna@example.com&password=wrong'
done
# 401 401 401 401 429

curl -i -X POST localhost:8000/auth/token -d 'username=anna@example.com&password=secret123'
# HTTP/1.1 429 Too Many Requests
# retry-after: 60
# {"detail":"Слишком много попыток входа, попробуйте через минуту"}
```

Пятая попытка уже отклонена: первая была при входе за токеном выше. Даже верный пароль не поможет, пока не пройдёт минута.

## Как это работает

### Подключение

Клиент берётся из пакета `redis`:

```bash
pip install redis
```

Клиент Redis создаётся один раз на всё приложение. Внутри у него пул соединений, а отдаёт его [зависимость](../../frameworks/fastapi/dependencies.md), чтобы в тестах клиент можно было подменить:

```python
# app/core/cache.py
from redis.asyncio import Redis

from app.core.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_cache() -> Redis:
    return redis_client
```

```python
# app/api/deps.py
CacheDep = Annotated[Redis, Depends(get_cache)]
```

### Кэш с инвалидацией

Статистика считается одним запросом к PostgreSQL. Результат кладём в Redis как JSON, а схема Pydantic сама превращает его в строку и обратно:

```python
# app/services/stats.py
STATS_TTL_SECONDS = 60


def stats_key(user_id: int) -> str:
    return f'stats:user:{user_id}'


async def get_stats(session: AsyncSession, cache: Redis, owner: User) -> TaskStats:
    cached = await cache.get(stats_key(owner.id))
    if cached is not None:
        return TaskStats.model_validate_json(cached)

    query = select(func.count(), func.count().filter(Task.done)).where(Task.owner_id == owner.id)
    total, done = (await session.execute(query)).one()
    stats = TaskStats(total=total, done=done)

    await cache.set(stats_key(owner.id), stats.model_dump_json(), ex=STATS_TTL_SECONDS)
    return stats


async def invalidate_stats(cache: Redis, owner: User) -> None:
    await cache.delete(stats_key(owner.id))
```

Любое изменение задач сбрасывает кэш, поэтому пользователь не видит устаревших цифр:

```python
# app/services/tasks.py
async def create_task(session: AsyncSession, cache: Redis, owner: User, data: TaskCreate) -> Task:
    task = Task(**data.model_dump(), owner_id=owner.id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    await invalidate_stats(cache, owner)
    return task
```

Сброс идёт **после** `commit`. Если сбросить раньше, параллельный запрос может успеть положить в кэш старые данные до сохранения новых.

Срок жизни остаётся страховкой: если где-то забыли сбросить кэш, данные исправятся сами через минуту.

Ещё одна деталь: эндпоинт `/tasks/stats` объявлен **раньше** `/tasks/{task_id}`. Иначе FastAPI попробовал бы превратить `stats` в число `task_id` и ответил бы 422.

### Ограничение попыток входа

Проверка оформлена зависимостью и подключена только к эндпоинту входа:

```python
# app/api/deps.py
LOGIN_ATTEMPTS_PER_MINUTE = 5


async def limit_login_attempts(request: Request, cache: CacheDep) -> None:
    window = 60
    key = f'rate:login:{request.client.host}:{int(time.time() // window)}'
    async with cache.pipeline() as pipe:
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        attempts, _ = await pipe.execute()
    if attempts > LOGIN_ATTEMPTS_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Слишком много попыток входа, попробуйте через минуту',
            headers={'Retry-After': str(window)},
        )
```

```python
# app/api/routers/auth.py
@router.post('/token', dependencies=[Depends(limit_login_attempts)])
async def login(session: SessionDep, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    ...
```

`dependencies=[...]` подходит для зависимостей, результат которых эндпоинту не нужен: они только проверяют и могут остановить запрос. Заголовок `Retry-After` подсказывает клиенту, через сколько секунд повторить.

### Тесты

Тесты используют отдельную базу Redis (номер 15) и очищают её перед каждым тестом. Клиент подменяется так же, как сессия БД:

```python
# tests/conftest.py
@pytest.fixture
async def cache():
    cache = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await cache.flushdb()
    yield cache
    await cache.aclose()

# в фикстуре client:
app.dependency_overrides[get_cache] = lambda: cache
```

```python
# tests/test_cache.py
async def test_stats_are_cached_and_invalidated(client, cache, anna):
    await client.post('/tasks', json={'title': 'Купить хлеб'}, headers=anna)

    response = await client.get('/tasks/stats', headers=anna)
    assert response.json() == {'total': 1, 'done': 0}
    assert await cache.get('stats:user:1') == '{"total":1,"done":0}'

    await client.patch('/tasks/1', json={'done': True}, headers=anna)
    assert await cache.get('stats:user:1') is None
```

## Частые ошибки

- Новый клиент Redis на каждый запрос → каждый раз открывается соединение, и выигрыш от кэша съедается → создать клиент один раз на приложение и отдавать его зависимостью.
- Кэш, который никто не сбрасывает → пользователь создаёт задачу и не видит её в статистике до истечения срока → сбрасывать кэш во всех местах, где данные меняются, лучше в сервисном слое, а не в роутерах.
- Сброс кэша до `commit` → параллельный запрос кладёт в кэш старые данные, и они живут до истечения срока → вызывать `invalidate_stats` после `commit`.
- Ограничение по IP за прокси → за NGINX у всех запросов адрес прокси, и лимит становится общим на всех пользователей → брать адрес клиента из `X-Forwarded-For`, который ставит доверенный прокси (uvicorn: `--proxy-headers --forwarded-allow-ips`).
- Падение приложения, если Redis недоступен → один упавший контейнер кладёт весь сервис → для кэша перехватить ошибку соединения и сходить в базу напрямую: медленнее, но работает.
- Тесты ходят в ту же базу Redis, что и приложение → ключи из прошлых запусков ломают проверки → отдельный номер базы и `flushdb` перед каждым тестом.

## Когда не использовать

Пока приложение работает в одном процессе, а кэшируемые данные помещаются в память, Redis лишний: хватит словаря с TTL или `functools.lru_cache`, а лимит попыток можно считать в памяти процесса. Redis нужен, когда воркеров несколько (uvicorn с `--workers`, несколько контейнеров) и состояние должно быть общим.

Для данных, которые нельзя терять — задачи, пользователи, платежи, — Redis не замена PostgreSQL: кэш может быть сброшен в любой момент. А если кэшировать нужно целые HTTP-ответы для всех пользователей, проще поручить это [NGINX](../../web/nginx/reverse_proxy.md), не трогая код приложения.

## Связанные темы

- [Основы Redis](basics.md)
- [Пять типовых сценариев](scenarios.md)
- [Зависимости в FastAPI](../../frameworks/fastapi/dependencies.md)
- [NGINX как обратный прокси](../../web/nginx/reverse_proxy.md)
- [Кэширование](../../design/caching.md)
- [Ограничение частоты запросов](../../design/rate_limiting.md)
