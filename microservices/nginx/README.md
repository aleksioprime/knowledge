# NGINX

**NGINX** — высокопроизводительный веб-сервер, reverse proxy, балансировщик нагрузки и HTTP-кэш. Один из самых популярных серверов в продакшене.

Типовые сценарии:
- Reverse proxy перед бэкендом (uvicorn, gunicorn, Node.js)
- Балансировка нагрузки между апстримами (round-robin, least_conn, ip_hash)
- Раздача статики (быстрее и дешевле, чем бэкенд)
- SSL/TLS termination (Let's Encrypt + certbot)
- Кэширование ответов
- Защита от базовых атак (rate limiting, connection limiting)
- WebSocket-проксирование

## Содержание

> Заметки и примеры будут добавляться по мере проработки темы. Установка NGINX на Ubuntu есть в разделе [Linux](../../linux/docs/nginx_install.md).
