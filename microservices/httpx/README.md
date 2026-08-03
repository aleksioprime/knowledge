# HTTPX

**HTTPX** — современная HTTP-библиотека для Python, альтернатива `requests` с поддержкой асинхронных запросов, HTTP/2, таймаутов и продвинутого пулинга соединений.

Структура запросов и ответов, версии протокола, заголовки и HTTPS описаны в общем разделе [HTTP](../../web/http/README.md).

Особенности:
- Sync и async API (`httpx.Client`, `httpx.AsyncClient`)
- Поддержка HTTP/1.1 и HTTP/2
- Гибкие таймауты, повторы, прокси
- Совместимость с API `requests`
- Удобно для межсервисного взаимодействия в микросервисах

## Содержание

- [Пример: fastapi (Posts ↔ Categories service)](examples/fastapi/README.md)
- Пример: simple — `examples/simple/`
