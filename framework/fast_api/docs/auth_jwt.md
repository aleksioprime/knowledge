# Авторизация по JWT

У каждого пользователя «Задачника» свои задачи, поэтому API должен знать, кто прислал запрос. Отправлять логин и пароль с каждым запросом опасно и неудобно. Обычно пароль проверяют один раз и выдают взамен **токен** — подписанную строку «это пользователь №1, действует до 22:00». Дальше клиент прикладывает токен к каждому запросу, а сервер проверяет подпись.

Это серверная половина. Как хранить токен и отправлять его из фронтенда, описано в заметке [Авторизация во Vue](../../../vuejs/docs/auth.md).

```bash
pip install pyjwt "pwdlib[argon2]" python-multipart
```

## Минимальный пример

Весь процесс в «Задачнике»:

```bash
# 1. Регистрация
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email": "anna@example.com", "password": "secret123"}'
# {"id":1,"email":"anna@example.com"}

# 2. Вход: обмениваем пароль на токен
curl -X POST localhost:8000/auth/token -d 'username=anna@example.com&password=secret123'
# {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzkzMjE2NDg2fQ.Dh5u...","token_type":"bearer"}

# 3. Запросы с токеном
curl localhost:8000/tasks -H "Authorization: Bearer $TOKEN"
# [...]

curl localhost:8000/tasks
# 401 {"detail":"Not authenticated"}
```

## Что внутри токена

JWT (JSON Web Token) — три части через точку: заголовок, данные и подпись. Первые две — обычный JSON в кодировке base64, их может прочитать кто угодно:

```text
{"alg":"HS256","typ":"JWT"}     ← заголовок: алгоритм подписи
{"sub":"1","exp":1793216486}    ← данные: id пользователя и срок действия
Dh5uKT4gEQQRqri596aeTapz...     ← подпись
```

Подпись вычисляется из первых двух частей и **секретного ключа**, который знает только сервер. Изменить в токене `"sub":"1"` на `"sub":"2"` можно, но подпись тогда не сойдётся, и сервер токен отклонит. Отсюда два следствия:

- **токен нельзя подделать** без секретного ключа;
- **токен не шифруется** — не кладите в него ничего секретного.

## Как это устроено в коде

**Пароли хранятся только в виде хэша.** Хэш — односторонняя функция: из него нельзя получить пароль, но можно проверить, подходит ли пароль к хэшу. Алгоритм argon2 специально сделан медленным, чтобы перебор паролей по украденной базе был очень дорогим:

```python
# app/core/security.py
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

hashed = password_hash.hash('secret123')    # '$argon2id$v=19$m=65536,t=3,p=4$...'
password_hash.verify('secret123', hashed)    # True
password_hash.verify('wrong', hashed)        # False
```

Хэш одного и того же пароля каждый раз разный: в него подмешивается случайная «соль». Поэтому сравнивать хэши через `==` нельзя, только через `verify`.

**Выпуск и проверка токена:**

```python
# app/core/security.py
import jwt

ALGORITHM = 'HS256'


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({'sub': str(user_id), 'exp': expire}, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    return int(payload['sub'])
```

`jwt.decode` сам проверяет подпись и срок действия. Просроченный токен вызовет `ExpiredSignatureError`, подделанный — `InvalidSignatureError`. Обе ошибки — наследники `InvalidTokenError`.

**Вход.** `OAuth2PasswordRequestForm` принимает форму `username` + `password`. Это стандарт OAuth2, поэтому поле называется `username`, хотя мы кладём туда email. Зато кнопка **Authorize** в `/docs` работает сразу.

```python
# app/api/routers/auth.py
@router.post('/token')
async def login(session: SessionDep, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = await users.authenticate(session, form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Неверный email или пароль')
    return Token(access_token=create_access_token(user.id))
```

**Текущий пользователь** — [зависимость](dependencies.md), которую получает любой защищённый эндпоинт:

```python
# app/api/deps.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/token')


async def get_current_user(session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user_id = decode_access_token(token)
    user = await session.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный или просроченный токен',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```

`OAuth2PasswordBearer` достаёт токен из заголовка `Authorization: Bearer ...`, а если заголовка нет, отвечает 401 `Not authenticated`. Теперь защитить эндпоинт — значит добавить аргумент `user: CurrentUser`.

## Чего здесь нет

Схема из одного короткоживущего токена подходит для учебного проекта. В продакшене обычно добавляют:

- **refresh-токен** — долгоживущий токен, на который можно получить новый access-токен без повторного ввода пароля;
- **отзыв токенов** — JWT действует до истечения срока, даже если пользователь «вышел». Чтобы его отозвать, нужен чёрный список (например, в Redis) или короткий срок жизни;
- **ограничение попыток входа** — защита от перебора паролей;
- **внешний сервер авторизации** вроде [Keycloak](../../../microservices/keycloak/README.md), если сервисов много.

## Частые ошибки

- **Секретный ключ в коде.** Кто видел репозиторий, может выпускать токены за любого пользователя. Ключ — только в переменных окружения, длинный и случайный: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- **Токен без срока действия.** Украденный токен будет работать вечно. Всегда задавайте `exp`.
- **Разные ответы для «нет такого email» и «неверный пароль».** Так можно выяснить, кто зарегистрирован. Отвечайте одинаково.
- **Свой алгоритм хэширования.** `sha256(password)` перебирается на видеокарте за минуты. Используйте argon2 или bcrypt через готовую библиотеку.
- **Не указать `algorithms` в `jwt.decode`.** Без явного списка алгоритмов возможны атаки с подменой алгоритма. PyJWT требует этот параметр именно поэтому.

## Связанные темы

- [Авторизация во Vue](../../../vuejs/docs/auth.md) — клиентская сторона
- [Заголовки и cookies](../../../web/http/headers_cookies_cache.md)
- [Атаки на браузер](../../../web/security/browser_attacks.md) — где безопаснее хранить токен
