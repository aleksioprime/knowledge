JWT (JSON Web Token) Authentication — это популярный метод авторизации в REST API, который использует JSON Web Tokens для проверки подлинности пользователей и предоставления им доступа к защищенным ресурсам. В отличие от традиционных методов, основанных на сессиях, JWT не требует хранения информации о сессии на сервере, что делает его более масштабируемым и гибким.

**Как работает JWT Authentication:**

1. **Аутентификация:** Пользователь предоставляет свои данные (например, имя пользователя и пароль) серверу аутентификации.
2. **Генерация токена:** Если данные правильны, сервер генерирует JWT токен и отправляет его клиенту. Этот токен является зашифрованным JSON-объектом, содержащим информацию о пользователе и правах доступа.
3. **Авторизация:** Клиент включает JWT токен в заголовках запросов к защищенным ресурсам REST API (обычно в заголовке  `Authorization: Bearer <токен>`).
4. **Проверка токена:** Сервер проверяет подлинность и действительность полученного JWT токена. Этот процесс обычно включает проверку подписи токена и проверку срока его действия.
5. **Доступ к ресурсам:** Если токен действителен, сервер предоставляет клиенту доступ к запрошенным ресурсам.

JSON Web Tokens (JWT) — это популярный стандарт для передачи информации аутентификации между сторонами, часто используемый в RESTful API. Его популярность обусловлена рядом преимуществ:

- **Компактность и лёгкость:** JWT — это компактный формат, легко генерируемый и проверяемый. Он представляет собой строку JSON, кодированную с помощью Base64.
- **Самодостаточность:** JWT содержит всю необходимую информацию для аутентификации и авторизации в одной строке. Это отличается от традиционных методов, где серверу приходится хранить сессионные данные пользователей.
- **Децентрализованность:** JWT не требует хранения информации на сервере. Это значительно упрощает масштабирование системы и повышает надёжность. Сервер не перегружается хранением сессий, а просто проверяет токен.
- **Простота интеграции:** JWT легко интегрируется в различные системы и приложения. Существует множество библиотек для работы с JWT на разных языках программирования.
- **Стандартизация:** JWT является стандартным форматом, описанным в RFC 7519. Это позволяет различным системам легко взаимодействовать друг с другом с использованием JWT.
- **Гибкость:** JWT позволяет хранить различную информацию, не только идентификатор пользователя. Можно добавлять роли, права доступа и другие данные, необходимые для авторизации.
- **Безопасность:** JWT может быть подписан цифровой подписью для защиты от подделки. Использование алгоритмов с симметричными или асимметричными ключами гарантирует целостность и подлинность токенов.

JWT обычно имеет заголовок (`HEADER`), полезную нагрузку (`PAYLOAD`) и подпись (`SIGNATURE`), разделенные точками, формат выглядит следующим образом:

```sh
header.payload.signature
```

### Генерация секретного ключа

Секретный ключ представляет собой закодированную строку, созданную вручную, и ее следует хранить отдельно на сервере авторизации.

`openssl` — подходящая утилита для генерации этого длинного и рандомного ключа. Запустим следующую команду, чтобы создать ключ:

```sh
openssl rand -hex 32
```

В нашем проекте мы будем хранить секретный ключ и тип алгоритма в переменных

```ini
SECRET_KEY = 'a21679097c1ba42e9bd06eea239cdc5bf19b249e87698625cba5e3572f005544'
ALGORITHM = 'HS256'
```

В рамках расширения JWT Python мы выбрали модуль [`PyJWT`](https://pypi.org/project/PyJWT/) для генерации токена, поскольку он надежен и имеет дополнительные криптографические функции, которые могут подписывать сложное содержимое данных. Прежде чем использовать этот модуль, сначала установим его с помощью команды pip.

```sh
pip install PyJWT
```

Пример работы:

```python
from datetime import datetime, timedelta, timezone
import jwt


async def create_access_token(username: str, user_id: int, is_admin: bool, is_supplier: bool, is_customer: bool,
                              expires_delta: timedelta):
    payload = {
        'sub': username,
        'id': user_id,
        'is_admin': is_admin,
        'is_supplier': is_supplier,
        'is_customer': is_customer,
        'exp': datetime.now(timezone.utc) + expires_delta
    }

    # Преобразование datetime в timestamp (количество секунд с начала эпохи)
    payload['exp'] = int(payload['exp'].timestamp())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

```python
@router.post('/token')
async def login(db: Annotated[AsyncSession, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(db, form_data.username, form_data.password)

    token = await create_access_token(user.username, user.id, user.is_admin, user.is_supplier, user.is_customer,
                                expires_delta=timedelta(minutes=20))
    return {
        'access_token': token,
        'token_type': 'bearer'
    }
```

Проверка токена

```python
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get('sub')
        user_id: int | None = payload.get('id')
        is_admin: bool | None = payload.get('is_admin')
        is_supplier: bool | None = payload.get('is_supplier')
        is_customer: bool | None = payload.get('is_customer')
        expire: int | None = payload.get('exp')

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user'
            )
        if expire is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token supplied"
            )

        if not isinstance(expire, int):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token format"
            )

        # Проверка срока действия токена
        current_time = datetime.now(timezone.utc).timestamp()

        if expire < current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired!"
            )

        return {
            'username': username,
            'id': user_id,
            'is_admin': is_admin,
            'is_supplier': is_supplier,
            'is_customer': is_customer,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired!"
        )
    except jwt.exceptions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate user'
        )
```

Декодируем полученный токен в словарь `payload`, используя секретный ключ и алгоритм. Далее мы извлекаем содержимое ключей словаря, и запускаем проверки. Сначала функция проверяет ключи username и user_id. Если содержимое данных ключей не найдено, то вызываем ошибку валидации пользователя. Далее функция проверяет срок действия токена. Если срок действия не указан, значит, токен не был предоставлен. Следующая проверка — валидность токена — генерируется исключение, информирующее пользователя об истечении срока действия токена. Если токен действителен, возвращается декодированная полезная нагрузка.

В блоке except для любой ошибки JWT выдается исключение неверного запроса.

`get_current_user()` должен быть внедрен в каждую реализацию сервиса, чтобы ограничить доступ пользователей. Но на этот раз метод не только проверит учетные данные, но и выполнит декодирование полезной нагрузки JWT.