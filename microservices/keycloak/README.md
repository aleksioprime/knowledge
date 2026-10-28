# Keycloak

В [«Задачнике»](../../pet/tasker/README.md) регистрация, хранение паролей и выпуск JWT написаны прямо в приложении. Для одного сервиса это нормально. Но когда сервисов пять, а ещё нужны вход через Google, двухфакторная аутентификация, сброс пароля и админка пользователей, писать это в каждом сервисе — плохая идея. Keycloak — отдельный сервер авторизации: он хранит пользователей, проверяет пароли и выдаёт токены, а сервисам остаётся только проверить подпись токена.

Пример — в папке [example](example/): Keycloak с готовым realm и небольшой сервис на FastAPI.

```bash
cd example
docker compose up -d
```

Через полминуты откроется админка: http://localhost:8080 (логин и пароль `admin`).

## Минимальный пример

Получаем токен у Keycloak:

```bash
curl -X POST localhost:8080/realms/tasker/protocol/openid-connect/token \
  -d grant_type=password -d client_id=tasker-api -d username=anna -d password=secret123
```

```json
{"access_token": "eyJhbGciOiJSUzI1NiIs...", "expires_in": 300, "refresh_token": "eyJhbGciOiJIUzUxMiIs...", "token_type": "Bearer", ...}
```

Идём с ним в свой сервис:

```bash
uvicorn api:app --port 8020

curl localhost:8020/me -H "Authorization: Bearer $TOKEN"
# {"id":"a6d6192c-...","username":"anna","roles":["user"]}

curl -X DELETE localhost:8020/admin/tasks -H "Authorization: Bearer $TOKEN"
# 403 {"detail":"Нужна роль admin"}
```

С токеном пользователя `boris`, у которого есть роль `admin`, тот же запрос вернёт 200.

## Как это работает

**Realm** — изолированное пространство со своими пользователями, ролями и настройками. Обычно один realm на продукт. Здесь realm `tasker` создаётся при старте из файла [realm-tasker.json](example/realm-tasker.json).

**Клиент** — приложение, которое просит токены. Клиент `tasker-api` публичный (без секрета), как фронтенд в браузере.

**Роли** назначаются пользователям и попадают в токен. Сервис читает их из токена и сам решает, что разрешить.

Внутри access-токена:

```json
{
  "iss": "http://localhost:8080/realms/tasker",
  "aud": "tasker-api",
  "sub": "a6d6192c-bedb-4cb6-baae-74199279bf99",
  "preferred_username": "anna",
  "realm_access": {"roles": ["user"]},
  "exp": 1793216026
}
```

Главное отличие от «Задачника» — алгоритм подписи. Там токен подписан **секретным ключом** (HS256): проверить его может только тот, кто знает секрет. Keycloak подписывает **закрытым ключом** (RS256), а **открытые ключи** публикует по адресу:

```text
http://localhost:8080/realms/tasker/protocol/openid-connect/certs
```

Поэтому любой сервис может проверить токен, не зная никаких секретов и даже не обращаясь к Keycloak на каждый запрос: ключи скачиваются один раз и кэшируются.

## Проверка токена в FastAPI

```python
# example/api.py
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ISSUER = 'http://localhost:8080/realms/tasker'
AUDIENCE = 'tasker-api'

# Открытые ключи Keycloak: клиент скачает их один раз и закэширует
jwks_client = jwt.PyJWKClient(f'{ISSUER}/protocol/openid-connect/certs')
bearer = HTTPBearer()

app = FastAPI(title='Задачи с Keycloak')


def get_claims(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> dict:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=['RS256'], audience=AUDIENCE, issuer=ISSUER)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=f'Неверный токен: {error}')


Claims = Annotated[dict, Depends(get_claims)]


def require_role(role: str):
    def checker(claims: Claims) -> dict:
        if role not in claims.get('realm_access', {}).get('roles', []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f'Нужна роль {role}')
        return claims
    return checker


@app.delete('/admin/tasks', dependencies=[Depends(require_role('admin'))])
def clear_all_tasks() -> dict:
    return {'deleted': 'все задачи'}
```

`jwt.decode` проверяет всё сразу: подпись, срок действия, издателя (`iss`) и получателя (`aud`). Попытка дописать себе роль в токен ломает подпись:

```text
401 {"detail":"Неверный токен: Signature verification failed"}
```

`pip install "pyjwt[crypto]"` — для RS256 нужна библиотека `cryptography`.

## Как получают токены на самом деле

В примере токен получен по логину и паролю (`grant_type=password`). Так проще показать, но в настоящих приложениях этот способ не используют: пароль вводится не на странице Keycloak, а передаётся через ваше приложение, и в OAuth 2.1 этот способ убран.

Фронтенд использует **Authorization Code + PKCE**:

1. пользователь нажимает «Войти», и браузер переходит на страницу входа Keycloak;
2. после входа Keycloak возвращает браузер на `redirectUris` с одноразовым кодом;
3. фронтенд обменивает код на токены.

Пароль видит только Keycloak. Готовые библиотеки (`keycloak-js`, `oidc-client-ts`) делают это за вас. Как хранить токен на клиенте — в заметке [Авторизация во Vue](../../vuejs/docs/auth.md).

Сервисы между собой получают токены по **Client Credentials**: у сервиса есть свой клиент с секретом, и токен выдаётся сервису, а не пользователю.

## Частые ошибки

- **Нет проверки `aud`.** Токен, выданный для другого приложения того же realm, подойдёт и к вашему. Добавьте в клиент маппер аудитории (в примере — `oidc-audience-mapper`) и проверяйте `audience`.
- **Разный `iss` внутри и снаружи Docker.** Токен, полученный через `localhost:8080`, содержит `iss: http://localhost:8080/...`. Сервис в контейнере обращается к `keycloak:8080` и ожидает другой `iss` — проверка падает. Задайте Keycloak единый публичный адрес (`KC_HOSTNAME`) и проверяйте именно его.
- **Запрос к Keycloak на каждую проверку.** Эндпоинт introspection медленный и делает Keycloak узким местом. Проверяйте подпись локально по JWKS, как в примере.
- **Режим `start-dev` в продакшене.** Он использует встроенную базу и HTTP без TLS. Для работы нужен `start` с PostgreSQL и HTTPS.
- **401 или 403 без токена.** `HTTPBearer` в FastAPI 0.115 без заголовка `Authorization` отвечает `403 Not authenticated`, а в новых версиях — 401. Не завязывайте логику клиента на конкретный код.

## Связанные темы

- [Авторизация по JWT в FastAPI](../../framework/fast_api/docs/auth_jwt.md) — тот же JWT, но выпускает его само приложение
- [Авторизация во Vue](../../vuejs/docs/auth.md)
- [API Gateway](../api_gateway/README.md) — проверка токена на входе в систему
