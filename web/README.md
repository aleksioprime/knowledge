# Веб-протоколы и инфраструктура

Раздел о том, как клиент и сервер обмениваются данными по HTTP, как защищать веб-приложения и как принимать трафик через NGINX.

## Содержание

- [HTTP](http/README.md) — запросы и ответы, версии протокола, заголовки, HTTPS, передача файлов, проектирование API (REST, версионирование, gRPC)
- [Веб-безопасность](security/README.md) — атаки на браузер и сервер, защитные заголовки, криптография и пароли, OAuth и OpenID Connect, 2FA, персональные данные
- [NGINX](nginx/README.md) — reverse proxy, статика, TLS, балансировка и ограничение трафика

## Связанные разделы

- [HTTPX](../microservices/httpx/README.md) — HTTP-клиент для Python
- [API Gateway](../microservices/api_gateway/README.md) — единая точка входа в микросервисную систему
- [Postman](../tests/postman/README.md) — ручное и автоматизированное тестирование HTTP API
- [Сокеты в Python](../python/multitask/sockets.ipynb) — низкоуровневое сетевое взаимодействие
- [Установка NGINX на Ubuntu](../linux/docs/nginx_install.md) — эксплуатационная инструкция
