# Сессии на JWT: refresh, выход, роли

В заметке [Авторизация по JWT](auth_jwt.md) сервер выдаёт один access-токен и забывает о нём. Для настоящего сервиса этого мало. Пользователь нажал «Выйти», а токен продолжает работать. Телефон украли, и нужно закрыть все сессии. Токен живёт 15 минут, значит, пароль придётся вводить каждые 15 минут. Менеджеру нужно право удалять чужие задачи, а обычному пользователю — нет.

Здесь эти задачи решаются в отдельном Auth-сервисе: PostgreSQL хранит пользователей, роли и историю входов, Redis — сессии и отозванные токены. Весь код — в [примере](examples/auth_service/README.md), его тесты проходят.

```bash
pip install fastapi "pydantic[email]" "sqlalchemy[asyncio]" asyncpg pyjwt "pwdlib[argon2]" redis
```

## Минимальный пример

```bash
curl -s -X POST localhost:48000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"anna@example.com","password":"secret123"}'
# {"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"bearer"}

# access кончился — меняем refresh на новую пару, пароль не нужен
curl -s -X POST localhost:48000/auth/refresh -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$REFRESH\"}"
# {"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"bearer"}

# тот же refresh второй раз — сессия закрывается целиком
curl -s -X POST localhost:48000/auth/refresh -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$REFRESH\"}"
# {"detail":"Refresh-токен уже использован, сессия завершена"}

# у обычного пользователя нет права удалять задачи
curl -s -X DELETE localhost:48000/tasks/1 -H "Authorization: Bearer $ACCESS"
# {"detail":"Нужно право tasks:delete"}   ← 403
```

Что внутри пары, если раскодировать вторую часть токенов:

```text
access:  {"sub":"1","sid":"5b6aa621...","type":"access","roles":["user"],"ver":0,"jti":"0de12f30...","iat":1793224196,"exp":1793225096}
refresh: {"sub":"1","sid":"5b6aa621...","type":"refresh","jti":"27e65bb8...","iat":1793224196,"exp":1795816196}
```

- `sid` — номер сессии: одного входа с одного устройства. Он одинаков у всех токенов, выданных в рамках этого входа.
- `jti` — уникальный номер самого токена. По нему токен можно отозвать.
- `type` — чтобы refresh нельзя было подсунуть вместо access и наоборот.
- `ver` — версия токенов пользователя, нужна для «выйти со всех устройств».
- access живёт 15 минут (`exp - iat = 900`), refresh — 30 дней.

## Как это работает

### Сессии в базе или JWT

Классическая **серверная сессия**: после входа сервер кладёт запись в базу и отдаёт клиенту случайный идентификатор в cookie. На каждый запрос сервер ищет запись. Выйти — значит удалить запись, и сессия умирает мгновенно. Цена — поход в хранилище на каждый запрос, и это хранилище должно быть доступно всем сервисам.

**JWT** проверяется подписью без хранилища: любой сервис с ключом сам решает, пускать ли запрос. Это удобно в микросервисах, но теряется главное — **мгновенный отзыв**. Подписанный токен действителен до `exp`, что бы ни случилось.

На практике берут середину:

1. **Access** — короткий (минуты), многоразовый, проверяется только подписью. Если его украли, вред ограничен сроком жизни.
2. **Refresh** — длинный (дни), одноразовый, и сервер **помнит** его в хранилище. Получить новый access без пароля можно только через сервер, и тут он может отказать.
3. **Список отозванных access** (denylist) — для случаев, когда ждать 15 минут нельзя: выход, смена пароля. Список маленький: в нём только отозванные токены и только до их `exp`.

Получается, что хранилище нужно редко: при обновлении пары и при проверке denylist. Последняя — одна команда `EXISTS` в Redis, её можно и пропустить там, где 15 минут риска допустимы.

### Ротация refresh и повторное использование

Если refresh-токен многоразовый, то украденный работает 30 дней, и никто этого не заметит. Поэтому при каждом обновлении сервер выдаёт **новый** refresh, а старый перестаёт действовать. Это **ротация** (refresh token rotation).

Ротация даёт и сигнал тревоги. Настоящий клиент всегда приходит с последним выданным refresh. Если пришёл уже использованный, значит, копия токена есть у двух сторон: у клиента и у того, кто его украл. Кто из них кто, сервер не знает, поэтому закрывает **всю сессию** — все токены, выданные начиная с этого входа (в англоязычных текстах это «семейство токенов», token family). Злоумышленник теряет доступ, а настоящий пользователь просто войдёт заново.

```text
вход        → refresh R1               сессия: текущий R1
обновление R1 → refresh R2             сессия: текущий R2
обновление R1 (украденный) → R1 ≠ R2 → сессия удалена, R2 тоже не работает
```

В сессии хранится `jti` текущего refresh. Обновление сравнивает его с пришедшим и записывает новый. Сравнить и записать нужно **одной** операцией, иначе два параллельных запроса с одним refresh оба увидят «совпало». В Redis для этого есть Lua-скрипт, он выполняется целиком без вмешательства других команд:

```python
# app/services/sessions.py
ROTATE_SCRIPT = """
local current = redis.call('HGET', KEYS[1], 'refresh_jti')
if not current then return -1 end
if current ~= ARGV[1] then return 0 end
redis.call('HSET', KEYS[1], 'refresh_jti', ARGV[2], 'access_jti', ARGV[3], 'access_exp', ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""
```

```python
# app/api/routers/auth.py
@router.post('/refresh')
async def refresh(session: SessionDep, store: StoreDep, data: RefreshIn) -> TokenPair:
    payload = decode_token(data.refresh_token, 'refresh')
    if payload is None:
        raise unauthorized()
    user = await session.get(User, int(payload['sub']))
    if user is None or not user.is_active:
        raise unauthorized()

    sid = payload['sid']
    access = create_access_token(user.id, sid, user.role_names, await store.token_version(user.id))
    new_refresh = create_refresh_token(user.id, sid)
    result = await store.rotate(sid, payload['jti'], new_refresh.jti, access.jti, access.exp)
    if result is Rotation.REUSED:
        await store.revoke(sid)
        raise unauthorized('Refresh-токен уже использован, сессия завершена')
    if result is Rotation.UNKNOWN:
        raise unauthorized('Сессия завершена')
    return TokenPair(access_token=access.token, refresh_token=new_refresh.token)
```

Роли для нового access читаются из базы, поэтому изменения ролей попадают в токен при ближайшем обновлении.

Ограничение: `revoke` кладёт в denylist только **последний** выданный в сессии access. Если злоумышленник успел получить свой access до того, как подмену заметили, тот доживёт до `exp`, то есть до 15 минут. Если это недопустимо, проверяйте на каждом запросе, что сессия `sid` ещё существует: тогда удаление сессии мгновенно убивает все её access-токены, но Redis нужен на каждый запрос во всех сервисах.

### Где хранить refresh-сессии

В Redis, по ключу `session:{sid}`, с TTL, равным сроку жизни refresh:

```text
session:{sid}         hash  user_id, refresh_jti, access_jti, access_exp, user_agent, ip, created_at
user:{id}:sessions    set   sid всех сессий пользователя — для «выйти везде» и списка устройств
user:{id}:token_ver   int   версия токенов пользователя
denylist:{jti}        "1"   отозванный access, TTL — до его exp
```

Почему Redis, а не таблица в PostgreSQL:

- **TTL из коробки.** Сессия, которую не обновляли 30 дней, исчезает сама, не нужна фоновая чистка таблицы.
- **Частые короткие записи.** Каждое обновление пары — перезапись. Для Redis это обычная нагрузка, для PostgreSQL — лишние версии строк и работа автоочистки (vacuum).
- **Атомарная проверка и замена** скриптом, без блокировок строк.
- **Потеря не катастрофична.** Если Redis перезапустится без сохранения на диск, пользователям придётся войти заново. Данные, которые терять нельзя (пользователи, роли, история), лежат в PostgreSQL.

Ключ — `sid`, а не `jti` refresh-токена: `jti` меняется при каждой ротации, а сессия остаётся той же.

### Выход

**Выход с текущего устройства** — удалить сессию и запретить текущий access:

```python
# app/services/sessions.py
async def revoke(self, sid: str) -> None:
    session = await self.redis.hgetall(f'session:{sid}')
    if not session:
        return
    await self.deny_access(session['access_jti'], int(session['access_exp']))
    await self.redis.delete(f'session:{sid}')
    await self.redis.srem(f'user:{session["user_id"]}:sessions', sid)


async def deny_access(self, jti: str, exp: int) -> None:
    ttl = exp - int(time.time())
    if ttl > 0:
        await self.redis.set(f'denylist:{jti}', 1, ex=ttl)
```

TTL записи в denylist равен оставшемуся сроку токена. Хранить её дольше бессмысленно: после `exp` токен отклонит сама проверка подписи.

**Выход со всех устройств** — удалить все сессии из `user:{id}:sessions` и увеличить версию токенов. Все выданные access несут старое значение `ver`, и проверка их отклонит, хотя в denylist их нет:

```python
async def revoke_all(self, user_id: int) -> None:
    for sid in await self.redis.smembers(f'user:{user_id}:sessions'):
        await self.revoke(sid)
    await self.redis.delete(f'user:{user_id}:sessions')
    await self.redis.incr(f'user:{user_id}:token_ver')
```

Проверка access собирает всё вместе:

```python
# app/api/deps.py
async def get_access_payload(
    store: StoreDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if credentials is None:
        raise unauthorized('Нет токена')
    payload = decode_token(credentials.credentials, 'access')
    if payload is None:
        raise unauthorized()
    if await store.is_denied(payload['jti']):
        raise unauthorized('Токен отозван')
    if payload['ver'] != await store.token_version(int(payload['sub'])):
        raise unauthorized('Токен отозван')
    return payload
```

Другой сервис «Задачника», который проверяет JWT сам, может делать то же самое, если ему открыт Redis Auth-сервиса на чтение. Если нет — он проверяет только подпись и `exp` и живёт с риском в 15 минут.

**Смена пароля** — частный случай «выйти везде». Пароль меняют, когда подозревают кражу, и все текущие сессии надо считать скомпрометированными:

```python
@router.post('/password', status_code=status.HTTP_204_NO_CONTENT)
async def change_password(session: SessionDep, store: StoreDep, user: CurrentUser, data: PasswordChangeIn) -> None:
    if not password_hash.verify(data.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Неверный текущий пароль')
    user.password_hash = password_hash.hash(data.new_password)
    await session.commit()
    await store.revoke_all(user.id)
```

Так же поступают при блокировке пользователя и при сбросе пароля через почту.

### История входов

Каждая попытка входа известного пользователя пишется в таблицу: когда, откуда, с какого устройства и удачно ли.

```python
# app/models.py
class LoginHistory(Base):
    __tablename__ = 'login_history'
    __table_args__ = (Index('ix_login_history_user_created', 'user_id', 'created_at'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    user_agent: Mapped[str] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(45))
    success: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

```bash
curl -s localhost:48000/auth/history -H "Authorization: Bearer $ACCESS"
# [{"user_agent":"Firefox","ip":"192.168.65.1","success":true,"created_at":"2026-10-28T21:49:56.350247Z"}]
```

Пользователь видит в профиле список входов и замечает чужой. Неудачные попытки тоже полезны: серия ошибок с незнакомого адреса — повод сменить пароль. Список активных сессий (`GET /auth/sessions`) показывает то же для текущего момента, и из него удобно сделать кнопку «завершить эту сессию».

Детали, о которых легко забыть:

- **IP за прокси.** За NGINX `request.client.host` — адрес прокси. Настоящий адрес приходит в `X-Forwarded-For`, и верить ему можно только от своего прокси: в uvicorn это `--proxy-headers` и `--forwarded-allow-ips`.
- **Вход через другой сервис.** Если пароль проверяет не браузер, а, например, Django-админка от имени пользователя, она должна передать `User-Agent` браузера, иначе в истории окажется `python-httpx/0.28.1`.
- **Таблица растёт без остановки**, а запросы почти всегда про последние записи. Индекс `(user_id, created_at)` помогает выборке, но не удалению старых данных. Обычно таблицу секционируют по месяцам и удаляют старые секции целиком — см. [секционирование в PostgreSQL](../../databases/postgres/partitioning.md).

### Роли и права

**RBAC** (role-based access control, управление доступом на основе ролей) — схема из трёх уровней: у пользователя есть роли, у роли — права. Проверяют всегда **право**, а не роль: код говорит «нужно `tasks:delete`», а какие роли его дают, решается данными.

```text
user    → tasks:read, tasks:write
manager → tasks:read, tasks:write, tasks:delete
admin   → tasks:read, tasks:write, tasks:delete, roles:manage
```

В базе это таблицы `users`, `roles`, `permissions` и две связующие: `user_roles`, `role_permissions`. Право удобно называть `ресурс:действие`.

Проверка — фабрика [зависимостей](dependencies.md): функция принимает код права и возвращает зависимость.

```python
# app/api/deps.py
def require_permission(code: str):
    async def checker(user: CurrentUser) -> User:
        if code not in user.permission_codes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f'Нужно право {code}')
        return user

    return checker
```

```python
@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: Annotated[User, Depends(require_permission('tasks:delete'))]) -> None:
    ...


# если пользователь в обработчике не нужен
@router.put('/{user_id}/roles/{role_name}', dependencies=[Depends(require_permission('roles:manage'))])
async def set_role(...): ...
```

401 и 403 — разные ответы: 401 «не знаю, кто вы» (нет токена, он просрочен или отозван), 403 «знаю, но нельзя».

#### Роль в токене или проверка в базе

Роль можно положить в access-токен (`"roles":["user"]`), и тогда любой сервис проверит права без запросов к Auth-сервису. Цена — **роль устаревает**: если у менеджера забрали роль, его токен продолжит говорить `manager` до конца своей жизни, то есть до 15 минут.

| Где проверять | Плюсы | Минусы |
|---|---|---|
| Роль из токена | нет запросов в базу, работает в любом сервисе | изменение роли действует только после обновления access |
| Права из базы на каждый запрос | изменение действует сразу | запрос к базе или Auth-сервису на каждый вызов |

В примере сделаны оба варианта. Роли лежат в токене для других сервисов, а сам Auth-сервис в `require_permission` читает права из базы: тест `test_role_change_applies_without_relogin` проверяет, что новая роль работает без повторного входа. Для чувствительных действий (назначение ролей, удаление пользователей) проверка по базе стоит своих запросов. Если роль нужно отобрать мгновенно и везде, её снятие можно совместить с `revoke_all`.

#### RBAC, ABAC и IdM

RBAC отвечает на вопрос «может ли пользователь с такой ролью делать такое действие». Но часто правило зависит от данных: «редактировать задачу может её автор или менеджер его отдела, и только пока задача не закрыта». Это **ABAC** (attribute-based access control, доступ на основе атрибутов): решение принимается по атрибутам пользователя, объекта и окружения. Обычно их сочетают: RBAC даёт грубые права, проверки владельца пишут в коде сервиса, где есть объект.

**IdM** (identity management, управление учётными записями) — системы и процессы вокруг пользователей в организации: кто заводит учётку новому сотруднику, кто согласует выдачу роли, кто и когда отзывает доступы уволившемуся, где журнал «кто дал права и зачем». Auth-сервис проверяет пароль и токены, IdM управляет тем, какие роли у кого должны быть. В небольшой системе роль IdM играет эндпоинт назначения ролей с правом `roles:manage`, в крупной компании — отдельный продукт, который синхронизирует роли с сервером авторизации вроде [Keycloak](../../microservices/keycloak/README.md).

### Где хранить токены на клиенте

Сервер выдаёт пару в JSON, но браузерному клиенту безопаснее получать refresh в cookie с флагами `HttpOnly`, `Secure`, `SameSite`: так его не прочитает JavaScript при XSS. Варианты и их минусы разобраны в заметке [Авторизация во Vue](../../../frontend/vue/auth.md#хранение-токенов-в-браузере).

### Тесты

Логику хранилища удобно проверять без сервера: [fakeredis](../../databases/redis/README.md) поддерживает Lua-скрипты (пакет `fakeredis[lua]`), а значит, и ротацию.

```python
# tests/unit/test_session_store.py
@pytest.fixture
async def store():
    redis = FakeAsyncRedis(decode_responses=True)
    yield SessionStore(redis, refresh_ttl=3600)
    await redis.aclose()


async def test_refresh_rotates_only_once(store):
    await store.create(1, 's1', 'r1', 'a1', int(time.time()) + 900, 'pytest', '127.0.0.1')

    assert await store.rotate('s1', 'r1', 'r2', 'a2', int(time.time()) + 900) is Rotation.OK
    assert await store.rotate('s1', 'r1', 'r3', 'a3', int(time.time()) + 900) is Rotation.REUSED
```

Сценарии целиком идут через HTTP против приложения: `httpx.AsyncClient` с `ASGITransport` и настоящими PostgreSQL и Redis из `docker-compose.yml`. Зависимости `get_session` и `get_redis` подменяются на тестовую базу и Redis под номером 15 — так же, как в [тестах «Задачника»](../../testing/pytest/README.md).

```python
# tests/integration/test_auth_flow.py
async def test_reused_refresh_kills_the_whole_session(client, make_user, login):
    await make_user('anna@example.com')
    stolen = await login('anna@example.com')
    fresh = (await client.post('/auth/refresh', json={'refresh_token': stolen['refresh_token']})).json()

    reuse = await client.post('/auth/refresh', json={'refresh_token': stolen['refresh_token']})
    assert reuse.json()['detail'] == 'Refresh-токен уже использован, сессия завершена'

    assert (await client.post('/auth/refresh', json={'refresh_token': fresh['refresh_token']})).status_code == 401
    assert (await client.get('/auth/me', headers=bearer(fresh))).status_code == 401


async def test_logout_makes_access_token_invalid(client, make_user, login):
    await make_user('anna@example.com')
    tokens = await login('anna@example.com')

    assert (await client.post('/auth/logout', headers=bearer(tokens))).status_code == 204

    response = await client.get('/auth/me', headers=bearer(tokens))
    assert response.status_code == 401
    assert response.json()['detail'] == 'Токен отозван'


async def test_role_without_permission_gets_403(client, make_user, login):
    await make_user('anna@example.com', 'user')
    await make_user('boss@example.com', 'manager')

    anna = await login('anna@example.com')
    assert (await client.delete('/tasks/1', headers=bearer(anna))).status_code == 403

    boss = await login('boss@example.com')
    assert (await client.delete('/tasks/1', headers=bearer(boss))).status_code == 204
```

```bash
pytest -q
# 13 passed
```

Кроме этих сценариев в примере проверены: refresh работает ровно один раз, «выйти везде» закрывает другие устройства, смена пароля отзывает сессии, история входов пишет `User-Agent`, а ответ `/auth/me` соответствует [контракту](../../microservices/contracts.md#контрактные-тесты), который ждёт Django-админка.

## Частые ошибки

- **Refresh без ротации.** Украденный токен работает весь срок жизни незаметно. Выдавайте новый refresh на каждом обновлении и закрывайте сессию при повторном использовании старого.
- **Проверить и обновить refresh двумя командами.** Два параллельных запроса с одним токеном пройдут оба: `GET`, сравнение в Python, `SET`. Нужна атомарная операция: Lua-скрипт, `WATCH`/`MULTI` или `UPDATE ... WHERE refresh_jti = :old` в SQL.
- **Refresh принимается вместо access.** Без поля `type` (или разных ключей подписи) долгоживущий refresh открывает весь API. Проверяйте тип токена.
- **Denylist без TTL.** Записи копятся вечно, хотя через 15 минут токен и так недействителен. TTL — до `exp` токена.
- **Выход только на клиенте.** Удалить токен из `localStorage` — не выход: копия токена продолжит работать. Отзывайте сессию на сервере.
- **Смена пароля не отзывает сессии.** Злоумышленник, ради которого пароль меняли, остаётся в системе со своим refresh.
- **Проверка ролей вместо прав.** `if 'admin' in user.roles` расползается по коду, и новую роль «аудитор» придётся вписывать во все проверки. Проверяйте права, а роли пусть их группируют.
- **Отвечать 403 на просроченный токен.** Клиент по 401 понимает, что нужно обновить пару, а 403 воспримет как «нельзя» и ничего не сделает.

## Когда не использовать

- **Одно приложение с серверными шаблонами** (например, Django без отдельного фронтенда). Обычная сессия в cookie проще и отзывается мгновенно; JWT ничего не добавит.
- **Много сервисов, внешние клиенты, вход через Google или корпоративный каталог.** Писать свой сервер авторизации долго и рискованно — возьмите [Keycloak](../../microservices/keycloak/README.md) или другой OAuth2/OIDC-сервер, а сервисы пусть только проверяют его токены.

## Связанные темы

- [Авторизация по JWT](auth_jwt.md) — хэширование паролей и устройство токена
- [Redis в FastAPI](../../databases/redis/fastapi.md) — ограничение попыток входа
- [Django: пользователи и внешняя аутентификация](../django/auth.md) — вход в админку через этот Auth-сервис
- [Контракты между сервисами](../../microservices/contracts.md)
- [Keycloak](../../microservices/keycloak/README.md) — готовый сервер авторизации
- [Атаки на браузер](../../web/security/browser_attacks.md) — XSS, CSRF и хранение токенов
