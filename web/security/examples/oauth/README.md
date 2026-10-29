# Вход через OpenID Connect: FastAPI + Keycloak

Пример к заметке [OAuth 2.0 и OpenID Connect](../../oauth.md). Keycloak играет роль внешнего провайдера (как Яндекс ID или Google), FastAPI-приложение «Задачника» — клиента. Полный цикл: Authorization Code + PKCE + `state` + `nonce`, проверка `id_token` и привязка внешнего аккаунта к пользователю.

| Файл | Что внутри |
| --- | --- |
| [docker-compose.yaml](docker-compose.yaml) | Keycloak в режиме разработки с импортом realm |
| [realm-tasker-oauth.json](realm-tasker-oauth.json) | realm `tasker-oauth`, конфиденциальный клиент `tasker-web` с обязательным PKCE S256, пользователь `anna` |
| [app.py](app.py) | приложение на FastAPI и Authlib: `/login`, `/auth/callback`, `/me` |
| [run_flow.py](run_flow.py) | скрипт, который проходит вход как браузер и пробует несколько атак |

Учётные данные **только тестовые**: администратор Keycloak `admin` / `admin`, пользователь `anna` / `secret123`, секрет клиента `tasker-web-test-secret`.

## Запуск

```bash
docker compose up -d                       # Keycloak на http://localhost:8080
pip install -r requirements.txt
uvicorn app:app --port 8000
```

Через полминуты, когда Keycloak поднимется, откройте http://localhost:8000/login в браузере и войдите как `anna`. Или прогоните цикл скриптом:

```bash
python run_flow.py
```

Если порт 8080 занят, Keycloak можно поднять на другом — адрес передаётся приложению через переменную:

```bash
KEYCLOAK_PORT=38080 docker compose up -d
KEYCLOAK_URL=http://localhost:38080 uvicorn app:app --port 8000
```

Порт приложения должен быть именно 8000: `redirect_uri` в настройках клиента зарегистрирован точно как `http://localhost:8000/auth/callback`.

Остановить и удалить данные:

```bash
docker compose down -v
```

## Что выводит скрипт

```text
1. Редирект на провайдера: http://localhost:38080/realms/tasker-oauth/protocol/openid-connect/auth
  response_type = code
  client_id = tasker-web
  redirect_uri = http://localhost:8000/auth/callback
  scope = openid email profile
  state = ddJFrZwSEcIYQz9bWp41k702CWWPRI
  nonce = MHIoEbQkonqv9JAsguTu
  code_challenge = d7o3FVkDS_gGqDc333e7-CJ4sp9y0ghjq0XD1gwGYGQ
  code_challenge_method = S256

2. Провайдер возвращает на redirect_uri: http://localhost:8000/auth/callback
  state = ddJFrZwSEcIYQz9bWp41k702CWWPRI
  session_state = 5a66299e-f039-4179-b223-c2ff204316f0
  iss = http://localhost:38080/realms/tasker-oauth
  code = 27ef0ab1-7fdc-4998-9b15-b4772dfa7832.5a66299e-f039-4179-b223-c2ff204316f0.f5f71e2c-...

3. Ответ приложения: 200
{"user":{"id":1,"email":"anna@example.com","name":"Анна Иванова"},"id_token_claims":{...},"scope":"openid email profile"}

4. /me с cookie сессии: {"id":1,"email":"anna@example.com","name":"Анна Иванова"}

5. Тот же callback ещё раз: 400 {"detail":"mismatching_state: CSRF Warning! State not equal in request and response."}

6. Уже использованный code напрямую у провайдера: 400 {"error":"invalid_grant","error_description":"Code not valid"}

7. Callback без своего state: 400 {"detail":"mismatching_state: CSRF Warning! State not equal in request and response."}

8. Свежий code без code_verifier: 400 {"error":"invalid_grant","error_description":"PKCE code verifier not specified"}
```

Разбор шагов и полный `id_token` — в [заметке](../../oauth.md#пример-вход-в-задачник-через-keycloak).

## Особенности примера

- Keycloak ставит cookie с флагом `Secure`. Браузер считает `localhost` безопасным контекстом и отправляет такие cookie даже по http, а `httpx` — нет, поэтому `run_flow.py` передаёт их вручную.
- Пользователи и привязки внешних аккаунтов хранятся в словарях и пропадают при перезапуске. В настоящем приложении это таблицы `user` и `social_account`.
- Keycloak работает в режиме `start-dev` (HTTP, встроенная база) — только для разработки.
