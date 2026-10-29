# OAuth 2.0 и OpenID Connect: вход через внешний сервис

Пользователи «Задачника» просят кнопку «Войти через Яндекс». Задача в том, чтобы Яндекс подтвердил «это Анна, её почта такая-то», но пароль от Яндекса при этом не попал ни к нам, ни в наши логи. Если бы приложение спрашивало пароль от чужого сервиса, оно получило бы полный доступ к почте пользователя, а пользователь не смог бы этот доступ отозвать, не меняя пароль. OAuth 2.0 решает это так: пароль вводится только на странице провайдера, а приложение получает ограниченный и отзываемый токен. OpenID Connect (OIDC) поверх OAuth добавляет стандартный ответ на вопрос «кто это».

Рабочий пример — в папке [examples/oauth](examples/oauth/README.md): FastAPI-приложение входит через локальный Keycloak.

## Минимальный пример

Клиентская часть Authorization Code + PKCE на стандартной библиотеке: подготовка значений, ссылка на провайдера, проверка `state` и запрос токена.

```python run
import base64
import hashlib
import hmac
import secrets
from urllib.parse import urlencode

# 1. Подготовка: три случайных значения, сохраняются в сессии пользователя
session = {
    'state': secrets.token_urlsafe(24),
    'nonce': secrets.token_urlsafe(16),
    'code_verifier': secrets.token_urlsafe(48),
}
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(session['code_verifier'].encode()).digest()
).rstrip(b'=').decode()

# 2. Редирект на провайдера
params = {
    'response_type': 'code',
    'client_id': 'tasker-web',
    'redirect_uri': 'https://tasker.ru/auth/callback',
    'scope': 'openid email profile',
    'state': session['state'],
    'nonce': session['nonce'],
    'code_challenge': code_challenge,
    'code_challenge_method': 'S256',
}
print('https://provider/auth?' + urlencode(params))

# 4. Провайдер вернул браузер на redirect_uri с code и state
callback = {'code': '27ef0ab1-...', 'state': session['state']}
if not hmac.compare_digest(callback['state'], session['state']):
    raise PermissionError('state не совпадает: чужой или повторный callback')

# 5. Обмен кода на токены — с бэкенда, вместе с code_verifier
token_request = {
    'grant_type': 'authorization_code',
    'code': callback['code'],
    'redirect_uri': params['redirect_uri'],
    'code_verifier': session['code_verifier'],
    'client_id': 'tasker-web',
}
print(urlencode(token_request)[:80] + '...')
```

Провайдер (шаг 3) показывает пользователю форму входа и согласия, а затем возвращает браузер на `redirect_uri`. Запрос токена уходит `POST` с бэкенда, в ответ приходят `access_token`, `id_token` и обычно `refresh_token`. В приложении всё это делает библиотека (Authlib), но знать, какие значения и зачем она генерирует, нужно: именно их забывают при ручной реализации.

## Как это работает

### Немного истории

**OpenID 2.0** (2007) решал только задачу входа: пользователь вводил на сайте свой URL-идентификатор, сайт находил его провайдера, а тот подтверждал личность. Доступа к данным не давал, работал на XML и редиректах и не прижился.

**OAuth 1.0** (2007, RFC 5849) решал другую задачу — доступ приложения к данным пользователя без его пароля. Каждый запрос к API **подписывался** HMAC-SHA1 с секретом приложения и секретом токена, плюс nonce и метка времени. Это работало даже по голому HTTP, но было мучительно в реализации: параметры нужно было нормализовать и сортировать байт в байт как на сервере, а любая ошибка давала невнятное «invalid signature».

**OAuth 2.0** (2012, RFC 6749) отказался от подписи запросов и переложил защиту канала на TLS. Токен стал «предъявительским» (bearer): кто его предъявил, тот и владелец, поэтому без HTTPS OAuth 2.0 небезопасен. Зато клиент стал простым — заголовок `Authorization: Bearer ...`. Позже к нему добавили PKCE, рекомендации по безопасности (RFC 9700) и черновик OAuth 2.1, который убирает устаревшие сценарии.

**OpenID Connect** (2014) — слой поверх OAuth 2.0, который вернул «вход» в стандартном виде: `id_token`, `/userinfo`, discovery.

### Роли

- **Владелец ресурса (resource owner)** — пользователь, Анна.
- **Клиент (client)** — приложение, которое хочет доступ: «Задачник». Бывает **конфиденциальным** (бэкенд, может хранить `client_secret`) и **публичным** (SPA, мобильное приложение — секрет из них извлекается, поэтому его нет).
- **Сервер авторизации (authorization server)** — проверяет пользователя и выдаёт токены: Яндекс ID, Google, Keycloak.
- **Сервер ресурсов (resource server)** — API, который принимает access-токен: API Яндекс Диска или собственный API «Задачника», если токены выдаёт Keycloak.

Клиент заранее регистрируется у провайдера и получает `client_id`, `client_secret` (если конфиденциальный) и список разрешённых `redirect_uri`.

### Authorization Code + PKCE

Основной сценарий для всего, где есть пользователь и браузер.

**1. Подготовка.** Приложение генерирует три случайных значения и сохраняет их в сессии пользователя:

- `state` — защита от CSRF: провайдер вернёт его как есть, и приложение сверит;
- `nonce` — попадёт внутрь `id_token`, защита от подмены токена;
- `code_verifier` — секрет PKCE (43–128 символов). В запрос уходит только его хеш: `code_challenge = BASE64URL(SHA256(code_verifier))`.

**2. Редирект на провайдера.** Браузер уходит на `authorization_endpoint`:

```text
GET https://provider/auth
  ?response_type=code                         ← хотим одноразовый код
  &client_id=tasker-web
  &redirect_uri=http://localhost:8000/auth/callback
  &scope=openid email profile                 ← что просим; openid включает OIDC
  &state=ddJFrZwSEcIYQz9bWp41k702CWWPRI
  &nonce=MHIoEbQkonqv9JAsguTu
  &code_challenge=d7o3FVkDS_gGqDc333e7-CJ4sp9y0ghjq0XD1gwGYGQ
  &code_challenge_method=S256
```

**3. Вход и согласие.** Пользователь вводит пароль (и второй фактор) на странице провайдера и подтверждает, что разрешает приложению доступ к почте и профилю.

**4. Возврат с кодом.** Провайдер перенаправляет браузер на `redirect_uri`:

```text
GET http://localhost:8000/auth/callback?code=27ef0ab1-...&state=ddJFrZwSEcIYQz9bWp41k702CWWPRI
```

Код короткоживущий (секунды—минуты) и одноразовый. Он проходит через браузер, поэтому может засветиться в истории, логах прокси или в заголовке `Referer` — сам по себе он ещё не токен.

**5. Обмен кода на токены.** Приложение сверяет `state` с сохранённым и **со своего бэкенда** отправляет запрос на `token_endpoint`:

```text
POST https://provider/token
grant_type=authorization_code
&code=27ef0ab1-...
&redirect_uri=http://localhost:8000/auth/callback
&code_verifier=<исходная строка>
&client_id=tasker-web&client_secret=...
```

Провайдер хеширует `code_verifier` и сравнивает с `code_challenge` из шага 2. В ответ приходят `access_token`, `id_token` и обычно `refresh_token`.

**Зачем PKCE**, если код и так одноразовый: перехвативший код (вредоносное приложение с тем же URL-схемой на телефоне, утечка через логи) не сможет его обменять — у него нет `code_verifier`. Для публичных клиентов без секрета это единственная защита кода, поэтому сейчас PKCE рекомендуют всем клиентам, включая конфиденциальные.

### Другие сценарии

**Client Credentials** — пользователя нет, токен нужен самому сервису: сервис уведомлений ходит в API задач. Сервис отправляет `grant_type=client_credentials` со своим `client_id` и `client_secret` и получает access-токен от своего имени. Подробнее — в [Keycloak](../../microservices/keycloak/README.md#как-получают-токены-на-самом-деле).

**Device Code** (RFC 8628) — для устройств без браузера и удобной клавиатуры: телевизор, консольная утилита. Устройство получает `user_code` и показывает: «Откройте tasker.ru/device и введите ABCD-EFGH». Пока пользователь входит с телефона, устройство опрашивает `token_endpoint` и получает токен, когда вход завершён.

**Убранные сценарии** (их нет в OAuth 2.1, не используйте в новых проектах):

- **Implicit** — токен возвращался сразу в URL-фрагменте `#access_token=...`. Он оседал в истории браузера, утекал через `Referer` и расширения, и его нельзя было привязать к клиенту. Заменён на Authorization Code + PKCE.
- **Resource Owner Password Credentials** — приложение само спрашивает логин и пароль и отправляет их провайдеру. Это ровно то, от чего OAuth должен был избавить; к тому же так не работают 2FA и вход через третьи сервисы.

### OAuth — это авторизация, а не аутентификация

Access-токен OAuth говорит «предъявителю разрешено читать файлы Анны». Он не обязан говорить, кто такой предъявитель, для какого приложения выдан и когда пользователь входил. Формат access-токена OAuth вообще не определяет: это может быть случайная строка. Ранние «входы через OAuth» брали любой access-токен, ходили с ним в API профиля и верили результату — и злонамеренное приложение могло войти в чужой сервис с токеном, который пользователь выдал ему.

**OpenID Connect** добавляет то, чего не хватало:

- **`id_token`** — JWT, адресованный именно клиенту. Ключевые поля:
  - `iss` — кто выпустил (адрес провайдера);
  - `sub` — постоянный идентификатор пользователя у этого провайдера;
  - `aud` — для какого `client_id` выпущен; токен для другого приложения нужно отклонить;
  - `exp`, `iat`, `auth_time` — срок и время входа;
  - `nonce` — значение из запроса: защита от подстановки старого или чужого токена;
  - `email`, `name` и другие — если запрошены соответствующие scope.
- **`/userinfo`** — эндпоинт, который по access-токену возвращает профиль.
- **Discovery** — документ `/.well-known/openid-configuration` со всеми адресами и возможностями провайдера. Клиенту достаточно знать адрес провайдера.
- **JWKS** (`jwks_uri`) — открытые ключи, которыми проверяется подпись `id_token`. Про подписи открытым и закрытым ключом — в [Шифрование, хеширование и пароли](crypto.md#hs256-и-rs256-в-jwt).

Discovery локального Keycloak (фрагмент):

```text
issuer = http://localhost:38080/realms/tasker-oauth
authorization_endpoint = http://localhost:38080/realms/tasker-oauth/protocol/openid-connect/auth
token_endpoint = http://localhost:38080/realms/tasker-oauth/protocol/openid-connect/token
userinfo_endpoint = http://localhost:38080/realms/tasker-oauth/protocol/openid-connect/userinfo
jwks_uri = http://localhost:38080/realms/tasker-oauth/protocol/openid-connect/certs
code_challenge_methods_supported = ['plain', 'S256']
```

Не все провайдеры полностью реализуют OIDC: у части крупных сервисов вход построен на OAuth 2.0 и собственном эндпоинте профиля. Библиотеки вроде Authlib скрывают эти различия, но проверку `aud` и происхождения данных в таком случае приходится делать по документации провайдера.

### Пример: вход в «Задачник» через Keycloak

Keycloak здесь — внешний провайдер, как Яндекс ID. Клиент `tasker-web` конфиденциальный, с обязательным PKCE S256 и одним точным `redirect_uri`. Приложение на [Authlib](https://docs.authlib.org/):

```python
# examples/oauth/app.py (фрагмент)
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
# state, nonce и code_verifier живут в подписанной cookie между редиректами
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

oauth = OAuth()
oauth.register(
    name='keycloak',
    client_id='tasker-web',
    client_secret=CLIENT_SECRET,
    server_metadata_url=f'{ISSUER}/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile', 'code_challenge_method': 'S256'},
)

@app.get('/login')
async def login(request: Request):
    return await oauth.keycloak.authorize_redirect(request, str(request.url_for('auth_callback')))

@app.get('/auth/callback')
async def auth_callback(request: Request):
    try:
        # проверяет state, меняет code на токены с code_verifier,
        # проверяет подпись id_token по JWKS, iss, aud, exp и nonce
        token = await oauth.keycloak.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(400, detail=f'{error.error}: {error.description}')
    claims = token['userinfo']          # проверенные claims из id_token
    ...
```

Скрипт [run_flow.py](examples/oauth/run_flow.py) проходит цикл как браузер. Шаги 1–2 (параметры запроса и ответа) показаны выше в разделе про Authorization Code. Ответ приложения на шаге 3, `id_token_claims` отформатированы:

```json
{
  "exp": 1793224451, "iat": 1793224151, "auth_time": 1793224151,
  "jti": "1e3ed881-cbd3-46ba-80bd-e0ee06ce87be",
  "iss": "http://localhost:38080/realms/tasker-oauth",
  "aud": "tasker-web",
  "sub": "92f2ecc9-8616-436d-9ec7-d85455829c19",
  "typ": "ID",
  "azp": "tasker-web",
  "nonce": "MHIoEbQkonqv9JAsguTu",
  "sid": "5a66299e-f039-4179-b223-c2ff204316f0",
  "at_hash": "QA0xkFbhgr9vNT8uq4r-DQ",
  "acr": "1",
  "email_verified": true,
  "name": "Анна Иванова",
  "preferred_username": "anna",
  "given_name": "Анна",
  "family_name": "Иванова",
  "email": "anna@example.com"
}
```

`nonce` совпадает с тем, что ушёл в запросе, `aud` — наш `client_id`. `at_hash` — половина хеша access-токена: по нему проверяют, что access-токен пришёл в паре с этим `id_token`.

Попытки сломать цикл (фактический вывод):

```text
5. Тот же callback ещё раз: 400 {"detail":"mismatching_state: CSRF Warning! State not equal in request and response."}
6. Уже использованный code напрямую у провайдера: 400 {"error":"invalid_grant","error_description":"Code not valid"}
7. Callback без своего state: 400 {"detail":"mismatching_state: CSRF Warning! State not equal in request and response."}
8. Свежий code без code_verifier: 400 {"error":"invalid_grant","error_description":"PKCE code verifier not specified"}
```

Шаг 8 показывает PKCE в деле: перехвачен свежий код, атакующий знает даже `client_secret`, но без `code_verifier` обмен не проходит. Причём Keycloak после такой попытки аннулирует код, и легитимное приложение его уже тоже не обменяет — поэтому в скрипте для этой проверки делается отдельный вход. Запрос с чужим `redirect_uri` (`https://evil.example/cb`) Keycloak отклоняет ещё на странице входа: `400 Invalid parameter: redirect_uri`.

### Привязка внешнего аккаунта к пользователю

У провайдера свой пользователь, у «Задачника» — свой. Связь хранится в отдельной таблице:

```sql
CREATE TABLE social_account (
    id               bigserial PRIMARY KEY,
    user_id          bigint NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    provider         text   NOT NULL,          -- 'yandex', 'vk', 'google'
    provider_user_id text   NOT NULL,          -- claim sub
    created_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_user_id)
);
```

При входе ищем запись по паре `(provider, sub)`: нашли — входим под её `user_id`, не нашли — создаём пользователя или предлагаем привязать к существующему. Одному пользователю можно привязать несколько провайдеров.

**Почему не по email:**

- **захват аккаунта** — если провайдер не проверяет почту (или проверяет плохо), атакующий регистрируется там с почтой Анны, входит в «Задачник» и попадает в её аккаунт;
- **почта меняется** — у провайдера пользователь сменил адрес, и связь потерялась или, хуже, перешла к новому владельцу старого адреса;
- **почты может не быть** — пользователь не дал scope `email` или скрыл адрес (Apple выдаёт вместо настоящего адреса случайный адрес-пересылку).

`sub` уникален и постоянен в пределах `iss` — это и есть идентификатор. Почту можно использовать только как подсказку: «У нас уже есть аккаунт с этим адресом — войдите паролем, чтобы привязать Яндекс». Автоматически склеивать по почте допустимо разве что при `email_verified: true` от провайдера, которому вы доверяете, и это осознанный риск.

### Безопасность

- **`state` против CSRF.** Без него атакующий подсовывает жертве ссылку на callback со **своим** кодом, и жертва оказывается залогинена в аккаунт атакующего (login CSRF): всё, что она загрузит, достанется ему. `state` должен быть случайным, привязанным к сессии браузера и одноразовым. Подробнее о CSRF — в [Атаки на браузер](browser_attacks.md#csrf).
- **Точное совпадение `redirect_uri`.** Регистрируйте полные адреса без подстановочных знаков. Шаблон вида `https://tasker.ru/*` превращает любой открытый редирект на сайте в способ увести код на чужой домен. В учебном [примере Keycloak](../../microservices/keycloak/README.md) стоит `http://localhost:5173/*` — для разработки терпимо, для продакшена нет.
- **`client_secret` — только на бэкенде.** В переменных окружения или хранилище секретов, не в репозитории и никогда не в коде SPA или мобильного приложения. Публичные клиенты работают без секрета, только с PKCE. Для особо чувствительных систем вместо секрета используют подписанный JWT (`private_key_jwt`) или mTLS.
- **Проверка `id_token`.** Подпись по JWKS, `iss` совпадает с ожидаемым провайдером, `aud` содержит ваш `client_id`, `exp` не истёк, `nonce` совпадает с сохранённым. Библиотека делает это сама — не декодируйте `id_token` вручную без проверки.
- **Минимальные scope.** Просите только то, что нужно сейчас. Чем больше прав, тем меньше пользователей нажмут «Разрешить» и тем дороже утечка токена.
- **Токены провайдера не нужны — не храните.** Если вход нужен только для идентификации, после проверки `id_token` выпустите собственную сессию или токен и забудьте токены провайдера. Если храните refresh-токен для доступа к API провайдера — шифруйте его ([как](crypto.md#шифрование-полей-в-базе)).

## Частые ошибки

- **Вход по access-токену без OIDC.** Профиль, полученный по чужому access-токену, не доказывает, что токен выдан вашему приложению. Используйте `id_token` с проверкой `aud`.
- **`state` в виде константы или id пользователя.** Он должен быть непредсказуемым и одноразовым, иначе защита от CSRF не работает.
- **Коды и токены в логах.** Логи веб-сервера пишут полный URL callback вместе с `code`. Код одноразовый, но токены в логах уже прямая утечка — см. [Персональные данные](personal_data.md#типичные-причины-утечек).
- **Разные адреса провайдера внутри и снаружи Docker.** `iss` в токене не совпадёт с ожидаемым. То же, что в [Keycloak](../../microservices/keycloak/README.md#частые-ошибки).
- **Свой разбор протокола.** Ручная реализация обычно забывает что-то из `state`, `nonce`, PKCE или проверки подписи. Берите поддерживаемую библиотеку: Authlib, `python-social-auth`, `django-allauth`.

## Когда не использовать

Если сервис один и у пользователей нет аккаунтов у подходящих провайдеров, обычная регистрация по паролю ([JWT в FastAPI](../../frameworks/fastapi/auth_jwt.md)) проще.

Межсервисное взаимодействие внутри одной системы иногда проще закрыть mTLS или сетевыми политиками, чем поднимать сервер авторизации ради Client Credentials.

Убранные сценарии — Implicit и Resource Owner Password Credentials — не использовать в новых проектах: первый утекает через URL, второй отдаёт пароль приложению.

## Связанные темы

- [Keycloak](../../microservices/keycloak/README.md) — свой сервер авторизации
- [Авторизация во Vue](../../../frontend/vue/auth.md) — PKCE и хранение токенов на фронтенде
- [Шифрование, хеширование и пароли](crypto.md) — подписи HS256 и RS256
- [Двухфакторная аутентификация и капча](mfa.md)
- [HTTPS и TLS](../http/https_tls.md) — без TLS bearer-токены не защищены
