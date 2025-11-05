FastAPI поддерживает распространенные методы аутентификации: базовую HTTP-аутентификацию и аутентификацию на основе токенов:
- Базовая HTTP-аутентификация: В этом методе аутентификации учетные данные пользователя, которые обычно представляют собой имя пользователя и пароль, отправляются через HTTP-заголовок авторизации. Запрос, в свою очередь, возвращает заголовок WWW-Authenticate содержащий, базовое значение и необязательный параметр области, который указывает ресурс, к которому выполняется запрос аутентификации.
- Аутентификацию на основе токенов: Этот метод аутентификации включает использование токенов безопасности. Наиболее часто используемым токеном является JWT, который обычно представляет собой словарь, содержащий идентификатор пользователя и срок действия токена

## Регистрация пользователя

Пример модели пользователя:

```python
from app.backend.db import Base
from sqlalchemy import Column, Integer, String, Boolean


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_supplier = Column(Boolean, default=False)
    is_customer = Column(Boolean, default=True)
```

Пример pydantic-схемы данных для создания пользователя:

```python
class CreateUser(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    password: str
```

Пример эндпойнта для регистрации пользователя:

```python
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user import User
from app.schemas import CreateUser
from app.backend.db_depends import get_db

router = APIRouter(prefix='/auth', tags=['auth'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_user(db: Annotated[AsyncSession, Depends(get_db)], create_user: CreateUser):
    await db.execute(insert(User).values(first_name=create_user.first_name,
                                         last_name=create_user.last_name,
                                         username=create_user.username,
                                         email=create_user.email,
                                         hashed_password=bcrypt_context.hash(create_user.password),
                                         ))
    await db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }
```

Класс `CryptContext` предназначен для обработки многих более частых шаблонов кодирования, которые встречаются в приложениях, которым необходимо обрабатывать хэши паролей. В своей основе класс `CryptContext` - это просто набор объектов `PasswordHash`, импортированных по имени из модуля `passlib.hash`. 

Bcrypt — это функция шифрования, предназначенная для защиты паролей в базах данных. Она делает пароли нечитаемыми для тех, кто получит доступ к исходным данным.

Сегодня bcrypt считается самым надёжным способом шифрования паролей и часто используется по умолчанию в некоторых языках программирования.

Шифрование паролей нужно для того, чтобы защитить их при хранении на сервере или в базе данных. Когда вы создаёте пароль, он проходит через функцию шифрования и преобразуется в зашифрованный вид. Поскольку шифрование работает только в одном направлении, расшифровать зашифрованный пароль уже не получится.

Когда пользователь пытается войти в систему или требуется проверить его пароль, исходное значение поля, полученное при его вводе, хэшируется, и два хэша сравниваются. Если хэши одинаковы, то значит и пароль должен быть одинаковым.
## Базовая HTTP-аутентификация

Чтобы использовать базовую схему аутентификации, нам необходимо создать экземпляр класса `HTTPBasic` модуля и внедрить его в каждую службу API, чтобы защитить доступ к конечной точке.

Пример эндпойнта аутентификации пользователя:

```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


async def get_current_username(db: Annotated[AsyncSession, Depends(get_db)], credentials: HTTPBasicCredentials = Depends(security)):
    user = await db.scalar(select(User).where(User.username == credentials.username))
    if not user or not bcrypt_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


@router.get('/users/me')
async def read_current_user(user: dict = Depends(get_current_username)):
    return {'User': user}
```

Экземпляр `HTTPBasic`, внедренный в службы API, вызывает в браузере всплывающую форму входа, через которую мы вводим имя пользователя и пароль. Вход в систему заставит браузер отправить заголовок с учетными данными в приложение. Если приложение сталкивается с проблемой при его получении, схема `HTTPBasic` выдает код состояния `401` с сообщением «`Unauthorized`». Если при обработке формы нет ошибок, приложение должно получить заголовок `WWW-Authenticate` со значением введенных данных.

Мы добавили конечную точку `read_current_user`, которая будет выводить все данные авторизованного пользователя. То есть доступ к ней мы можем получить, только после авторизации. В ней, через зависимости, мы вызываем метод `get_current_username()`, чтобы проверить логин и пароль пользователя.

Мы подключаем две зависимости, первая это зависимость сессий БД, вторая это зависимость от экземпляра класса `HTTPBasic`, для извлечения `HTTPBasicCredentials` — объекта, содержащего сведения об имени пользователя и пароле из введенной формы в браузере. Далее мы выполняем запрос в нашу БД, получая пользователя на основе введенного имени пользователя. Далее мы проверяем введенный пароль `bcrypt_context.verify(credentials.password, user.hashed_password)`. Данный метод хэширует введенный пароль, и сверяет его с хэшем пароля этого пользователя из БД. В случае если пользователь не найден или проверка хэшей паролей не прошла, мы вызываем ошибку с кодом 401. В ином случае мы возвращаем объект пользователя, чтобы вывести его в конечной точке.

## Аутентификация OAuth2.0

Необходимо установить модуль `python-multipart`:

```
pip install python-multipart
```

Пример функци, которая будет получать имя пользователя и хэш пароля, и проверять их:

```python
async def authenticate_user(db: Annotated[AsyncSession, Depends(get_db)], username: str, password: str):
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not bcrypt_context.verify(password, user.hashed_password) or user.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

FastAPI поддерживает OAuth2, особенно тип потока паролей спецификации OAuth2. Его модуль `fastapi.security` имеет `OAuth2PasswordBearer`, который служит поставщиком аутентификации на основе пароля. Он также имеет `OAuth2PasswordRequestForm`, который может объявлять тело формы с обязательными параметрами, именем пользователя и паролем, а также некоторыми дополнительными параметрами, такими как `scope`, `grant_type`, `client_id` и `client_secret`.

Пример аутентификации:

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


@router.post('/token')
async def login(db: Annotated[AsyncSession, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(db, form_data.username, form_data.password)

    return {
        'access_token': user.username,
        'token_type': 'bearer'
    }
```

Функция `login()` получает логин и пароль, и через функцию `authanticate_user` проверяет равно ли значение полученного пароля хэшу пароля из БД запрошенной учетной записи. Если все проверки пройдены успешно, эндпоинт должен вернуть объект JSON с необходимыми свойствами `access_token` и `token_type`
## JWT-аутентификация

JWT (JSON Web Token) Authentication — это популярный метод авторизации в REST API, который использует JSON Web Tokens для проверки подлинности пользователей и предоставления им доступа к защищенным ресурсам. В отличие от традиционных методов, основанных на сессиях, JWT не требует хранения информации о сессии на сервере, что делает его более масштабируемым и гибким.

**Как работает JWT Authentication:**

1. **Аутентификация:** Пользователь предоставляет свои данные (например, имя пользователя и пароль) серверу аутентификации.
2. **Генерация токена:** Если данные правильны, сервер генерирует JWT токен и отправляет его клиенту. Этот токен является зашифрованным JSON-объектом, содержащим информацию о пользователе и правах доступа.
3. **Авторизация:** Клиент включает JWT токен в заголовках запросов к защищенным ресурсам REST API (обычно в заголовке  `Authorization: Bearer <токен>`).
4. **Проверка токена:** Сервер проверяет подлинность и действительность полученного JWT токена. Этот процесс обычно включает проверку подписи токена и проверку срока его действия.
5. **Доступ к ресурсам:** Если токен действителен, сервер предоставляет клиенту доступ к запрошенным ресурсам.

JSON Web Tokens (JWT) — это популярный стандарт для передачи информации аутентификации между сторонами, часто используемый в RESTful API

JWT обычно имеет заголовок (`HEADER`), полезную нагрузку (`PAYLOAD`) и подпись (`SIGNATURE`), разделенные точками, формат выглядит следующим образом:

```css
header.payload.signature
```

В рамках расширения JWT Python был выбран модуль [`PyJWT`](https://pypi.org/project/PyJWT/) для генерации токена, поскольку он надежен и имеет дополнительные криптографические функции, которые могут подписывать сложное содержимое данных.

Пример функции создания токена доступа:

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

 Конечная точка авторизации будет вызывать метод `create_access_token()` для запроса JWT. Служба входа предоставляет данные, обычно имя пользователя, которые составляют полезную часть токена. Поскольку JWT должен быть кратковременным, процесс должен обновить часть полезной нагрузки с истекшим сроком действия до некоторого значения даты и времени в минутах или секундах, подходящих для приложения.

Пример реализации функции авторизации:

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

В отличие от предыдущей схемах OAuth2, мы будем внедрять зависимость `get_current_user()` в каждую службу API, чтобы обеспечить безопасность и ограничить доступ. Внедренный экземпляр `OAuth2PasswordBearer` вернет JWT для извлечения полезных данных с использованием декодеров с указанным алгоритмом декодирования. Если токен подделан, изменен или срок его действия истек, метод вызовет исключение.

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

Мы декодируем полученный токен в словарь `payload`, используя секретный ключ и алгоритм. Далее мы извлекаем содержимое ключей словаря, и запускаем проверки. Сначала функция проверяет ключи username и user_id. Если содержимое данных ключей не найдено, то вызываем ошибку валидации пользователя. Далее функция проверяет срок действия токена. Если срок действия не указан, значит, токен не был предоставлен. Следующая проверка — валидность токена — генерируется исключение, информирующее пользователя об истечении срока действия токена. Если токен действителен, возвращается декодированная полезная нагрузка.

В блоке except для любой ошибки JWT выдается исключение неверного запроса.

Пример внедрения авторизации:

```python
@router.get('/read_current_user')
async def read_current_user(user: dict = Depends(get_current_user)):
    return {'User': user}
```