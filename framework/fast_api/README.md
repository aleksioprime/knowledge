# FastAPI

**FastAPI** — современный асинхронный веб-фреймворк для Python на базе Starlette и Pydantic. Поддерживает type hints, автоматическую генерацию OpenAPI/Swagger-документации, валидацию данных и dependency injection.

Ключевые особенности:
- Полностью асинхронный (async/await)
- Автогенерация документации (Swagger UI, ReDoc)
- Валидация запросов/ответов через Pydantic-модели
- Dependency Injection из коробки
- Высокая производительность (на уровне Node.js / Go)

## Содержание

- Примеры — `examples/`
- [TCP-соединения и порты](../../web/http/tcp_connections.md) — что происходит на уровне сети до того, как запрос дойдёт до FastAPI
