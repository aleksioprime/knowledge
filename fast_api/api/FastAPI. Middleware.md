Промежуточное программное обеспечение - это программное обеспечение, которое находится между вашим приложением и веб-сервером, перехватывая запросы и ответы по мере их прохождения. Среднее программное обеспечение может выполнять широкий спектр функций, от регистрации и аутентификации до кэширования и ограничения скорости.

В FastAPI промежуточное программное обеспечение находится перед конечными точками API, обрабатывая запросы и ответы. Когда поступает запрос, он проходит через уровень Middleware, прежде чем достичь конечной точки API. Аналогичным образом, когда ответ готов, он проходит через уровень Middleware, прежде чем быть отправленным обратно клиенту.

1. **CORSMiddleware**: Включает необходимые заголовки CORS в исходящих ответах для включения запросов с перекрестным исходным доступом из веб-браузеров.
2. **TrustedHostMiddleware**: Проверяет заголовок хоста входящих запросов для предотвращения потенциальных атак заголовка хоста HTTP.
3. **HTTPSRedirectMiddleware**:  Проверяет входящие запросы, чтобы они были на HTTPS. В ином случае выполнит редирект.
4. **SessionMiddleware**: Реализует подписанные HTTP-сеансы на основе файлов cookie, в которых данные сеанса читаемы, но не редактируются.
5. **GZip Middleware**: сжимает ответы для снижения использования трафика, что приводит к более быстрой передаче данных.

## CORS в FastAPI

Совместное использование ресурсов между источниками (CORS) служит правилом, которое предотвращает доступ незарегистрированных клиентов к ресурсу. Когда наш веб-API используется внешним приложением, браузер не разрешает HTTP-запросы из разных источников. Это означает, что доступ к ресурсам возможен только из точного источника, как API или источников, разрешенных API. FastAPI предоставляет CORSMiddleware, которое позволяет нам регистрировать домены, которые могут получить доступ к нашему API. Middleware принимает массив источников, которым будет разрешен доступ к ресурсам на сервере.

Параметры для CORS:

- `allow_origins`: Список источников (доменов), которым разрешен доступ к вашему API. Вы можете использовать `["*"]`, чтобы разрешить все источники, но это не рекомендуется по соображениям безопасности.
- `allow_methods`: Список методов HTTP, которые разрешены для запросов между различными источниками (cross-origin). По умолчанию он включает в себя `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`
- `allow_headers`: Список заголовков HTTP, которые разрешены для запросов между различными источниками. По умолчанию он включает в себя `["*"]`, что означает, что все заголовки разрешены.
- `allow_credentials`: Булевый флаг, указывающий, разрешены ли файлы cookie и заголовки авторизации для запросов между различными источниками. По умолчанию установлено значение `False`.
- `expose_headers`: Список заголовков HTTP, которые доступны браузеру в ответе. По умолчанию это пустой список.
- `max_age`: целое число, которое определяет максимальное количество секунд, в течение которых браузер может кэшировать Preflight запрос. По умолчанию он установлен на `600`.

Пример использования CORSMiddleware:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def main():
    return {"message": "Hello World"}
```

CORS - это полезная функция для веб-приложений, которым необходимо взаимодействовать с API, размещенными на разных серверах или доменах. FastAPI позволяет легко включать и настраивать CORS для ваших конечных точек API всего за несколько строк кода.

## TrustedHostMiddleware

Проверяет заголовок хоста входящих запросов для предотвращения потенциальных атак заголовка хоста HTTP.

```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["example.com", "*.example.com"]
)


@app.get("/")
async def main():
    return {"message": "Hello World"}
```

## HTTPSRedirectMiddleware

Обеспечивает, чтобы все входящие запросы были либо  `https` Вместо этого любые входящие запросы к  `http`  будут перенаправлены на `https`.

```python
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

app.add_middleware(HTTPSRedirectMiddleware)


@app.get("/")
async def main():
    return {"message": "Hello World"}
```

## GZip Middleware

Gzip - это алгоритм сжатия. Используется очень часто для сжатия контента, передаваемого через Интернет, и учитывая, что он поддерживается браузерами, то он способен сильно уменьшить размер файлов JavaScript, CSS и HTML.

```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/")
async def main():
    return "somebigcontent"
```

## SessionMiddleware

Сессия сайта — это механизм, который позволяет сайту помнить о пользователях и сохранять сделанные ими действия.

Сессии используются для разных целей, например:

- для сохранения введённых пользователем данных; 
- для настройки выдачи под интересы пользователя; 
- для показа персональных предложений в зависимости от действий на сайте.

Сессии делятся на два вида:

1. Временные. Существуют до тех пор, пока пользователь не закроет браузер.
2. Постоянные. Хранятся на компьютере в виде файлов cookie и могут быть использованы даже после выключения устройства.

Чтобы управлять данными сеанса, нам нужно создать отдельный сеанс с помощью SessionMiddleware от Starlette.

Starlette использует библиотеку `itsdangerous`:

```cmake
pip install itsdangerous
```

```python
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="7UzGQS7woBazLUtVQJG39ywOP7J7lkPkB0UmDhMgBR8=")
```

Аргументы:

- `secret_key`- Это случайная строка.
- `session_cookie`- По умолчанию "session".
- `max_age`- Время истечения срока действия сеанса в секундах. По умолчанию 2 недели. Если установлено `None`, то файл cookie будет длиться до тех пор, пока открыт сеанс браузера.
- `same_site`- Флаг SameSite не позволяет браузеру отправлять сеансовые файлы cookie вместе с запросами. По умолчанию `lax`".
- `https_only`- флаг Secure (может использоваться только с HTTPS). По умолчанию - `False`.
- `domain`- Домен файла cookie, используемый для совместного использования файлов cookie между поддоменами или кросс-доменами. Браузер по умолчанию использует домен для того же хоста, который установил файл cookie, за исключением ссылок на поддомены.

Добавление данных в сессию:

```python
@app.get("/create_session")
async def session_set(request: Request):
    request.session["my_session"] = "1234"
    return 'ok'
```

Чтение данных из сессии:

```python
@app.get("/read_session")
async def session_info(request: Request):
    my_var = request.session.get("my_session")
    return my_var
```

Удаление данных из сессии:

```python
@app.get("/delete_session")
async def session_delete(request: Request):
    my_var = request.session.pop("my_session")
    return my_var
```


## CustomMiddleware на основе классов

Middleware в FastAPI обрабатывает запросы перед их отправкой в определенные операции пути, и обрабатывает ответы перед их возвратом. Это делает его идеальным для общих операций, которые мы хотим выполнять по каждому запросу и ответу, таких как регистрация времени между запросом и его ответом.

```python
import time

class TimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        start_time = time.time()
        await self.app(scope, receive, send)
        duration = time.time() - start_time
        print(f"Request duration: {duration:.10f} seconds")
```

Важной частью этого класса является метод `__call__`, который реализует спецификацию приложения ASGI. Это асинхронная функция, которая принимает `scope`, `receive` и `send`. Эти параметры необходимы для запроса FastAPI. В этом простом Middleware мы просто передаем их в наше приложение FastAPI в  `self.app`.

Подлючение класса в проекте FastAPI:

```python
from fastapi import FastAPI
import time


class TimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        start_time = time.time()
        await self.app(scope, receive, send)
        duration = time.time() - start_time
        print(f"Request duration: {duration:.10f} seconds")


app = FastAPI()
app.add_middleware(TimingMiddleware)


@app.get("/hello")
async def greeter():
    return {"Hello": "World"}


@app.get("/goodbye")
async def farewell():
    return {"Goodbye": "World"}
```

## CustomMiddleware на основе функций

При создании промежуточного программного обеспечения на основе функций мы можем использовать декоратор `@app.middleware("http")`, поверх функции, чтобы указать, что функция будет действовать как промежуточное программное обеспечение. Это говорит FastAPI зарегистрировать функцию как компонент Middleware.

Кастомная функция Middleware, которая считает время выполнения запросов:

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()


@app.middleware("http")
async def modify_request_response_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    print(f"Request duration: {duration:.10f} seconds")
    return response


@app.get("/hello")
async def greeter():
    return {"Hello": "World"}


@app.get("/goodbye")
async def farewell():
    return {"Goodbye": "World"}
```

Функция промежуточного программного обеспечения получает два параметра:

- **request**: Содержит всю информацию и данные, связанные с входящим запросом.
- **call_next**: Вызывая функцию `call_next`, промежуточное программное обеспечение гарантирует, что запрос переходит к соответствующей операции пути и ждет результирующего ответа.