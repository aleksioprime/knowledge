# FastAPI

**FastAPI** — асинхронный веб-фреймворк для Python, построенный на Starlette и Pydantic. API описывается обычными функциями с подсказками типов, а FastAPI по ним проверяет входные данные, сериализует ответы и строит документацию OpenAPI (Swagger UI на `/docs`).

Заметки идут по порядку: каждая опирается на предыдущие. Примеры взяты из учебного проекта [«Задачник»](../../../practice/projects/tasker/README.md) — там весь код собран в работающее приложение с базой данных и тестами.

## Содержание

1. [Первое приложение](first_app.md) — эндпоинты, параметры пути и запроса, uvicorn, `def` и `async def`
2. [Схемы запросов и ответов](schemas.md) — тело запроса, фильтрация ответа, отдельные схемы для создания, обновления и чтения
3. [Зависимости](dependencies.md) — `Depends`, ресурсы с `yield`, цепочки проверок, подмена в тестах
4. [Ошибки и коды ответов](errors.md) — `HTTPException`, свои исключения и обработчики
5. [Структура проекта](structure.md) — роутеры, сервисы, настройки
6. [Авторизация по JWT](auth_jwt.md) — хэширование паролей, выпуск и проверка токенов
7. [Документация API](openapi.md) — метаданные, описания эндпоинтов и полей, ошибки в схеме, выгрузка `openapi.json` и проверка в CI
8. [Асинхронный сервис поиска на Elasticsearch](elasticsearch.md) — `lifespan`, слой сервисов, кэш ответов, пагинация, запуск в продакшене; [пример](examples/search_api/README.md)
9. [Сессии на JWT: refresh, выход, роли](auth_sessions.md) — пара access + refresh, ротация и повторное использование refresh, выход и «выйти везде», история входов, RBAC и `require_permission`; [пример Auth-сервиса](examples/auth_service/README.md)
10. [Уведомления в реальном времени](realtime.md) — polling, long polling, SSE и WebSocket, менеджер соединений, токен при подключении и код 1008, доставка между экземплярами через Redis pub/sub, догрузка пропущенного, пинги и nginx, лимит сообщений; [пример](examples/realtime/README.md)

### Примеры

- [Сервис поиска задач](examples/search_api/README.md) — FastAPI, Elasticsearch и Redis, функциональные тесты
- [Auth-сервис](examples/auth_service/README.md) — регистрация, сессии на JWT, роли, история входов
- [Уведомления в реальном времени](examples/realtime/README.md) — SSE и WebSocket, доставка через Redis pub/sub, nginx

## Связанные темы

- [Pydantic](../../../languages/python/typing/pydantic.md)
- [SQLAlchemy](../../databases/sqlalchemy/README.md) и [Alembic](../../databases/alembic/README.md) — база данных
- [Pytest](../../testing/pytest/README.md) — тестирование
- [TCP-соединения и порты](../../web/http/tcp_connections.md) — что происходит на уровне сети до того, как запрос дойдёт до FastAPI
