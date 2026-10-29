# Reverse proxy

Приложение на Uvicorn слушает порт 8000, но выставлять его наружу не хочется: порт нестандартный, HTTPS в нём нет, а медленный клиент занимает воркер на всё время передачи ответа. Reverse proxy решает это: NGINX принимает публичный запрос на порту 80 или 443 и передаёт его внутреннему приложению, а клиент к приложению напрямую не подключается.

## Минимальный пример

NGINX принимает запросы для `api.example.com` и передаёт их приложению на `127.0.0.1:8000`:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Проверка: `curl -H 'Host: api.example.com' http://localhost/` возвращает ответ приложения, а в его логах виден заголовок `X-Forwarded-For` с адресом клиента, а не `127.0.0.1`.

## Как это работает

Reverse proxy принимает публичный запрос и передаёт его внутреннему приложению. Клиент не подключается к приложению напрямую. Рабочий конфиг добавляет заголовки о клиенте и таймауты:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

Без `proxy_set_header` приложение видит соединение от NGINX: адрес `127.0.0.1`, схему `http` и `Host` вида `127.0.0.1:8000`. Заголовки `X-Forwarded-*` передают ему настоящие адрес клиента, схему и домен — они нужны для логов, ограничения частоты и правильных ссылок в ответах.

### `proxy_pass` и путь

Поведение зависит от завершающего `/`:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
}
```

Здесь запрос `/api/users` уйдёт upstream как `/users`. Без завершающего `/` в `proxy_pass` исходный URI сохраняется. Это различие следует явно проверять для каждой конфигурации.

### WebSocket

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }
}
```

### SSE и потоковые ответы

Для Server-Sent Events или другого потока часто требуется отключить буферизацию конкретного location:

```nginx
location /events {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_read_timeout 1h;
}
```

Глобально отключать буферизацию без необходимости не стоит: она защищает медленное приложение от медленных клиентов и может повышать пропускную способность.

## Частые ошибки

- Нет `proxy_set_header Host $host` → приложение получает `Host: 127.0.0.1:8000`, ссылки и редиректы ведут на внутренний адрес, проверка разрешённых хостов отклоняет запрос → всегда передавать `Host`, `X-Forwarded-For` и `X-Forwarded-Proto`.
- Приложение доверяет `X-Forwarded-For` без настройки → заголовок может подставить любой клиент, и ограничение частоты или логи видят чужой адрес → доверять заголовку только от адреса NGINX (в Uvicorn — `--forwarded-allow-ips`).
- Завершающий `/` в `proxy_pass` поставлен или забыт → приложение получает `/api/users` вместо `/users` или наоборот и отвечает 404 → проверить `curl`'ом один запрос после каждого изменения `location`.
- WebSocket без `Upgrade` и `Connection` → браузер получает 400 или соединение закрывается сразу → добавить `map $http_upgrade` и обе директивы `proxy_set_header`.
- `proxy_read_timeout` по умолчанию 60 секунд, а SSE-поток или долгий отчёт живут дольше → соединение рвётся с 504 → увеличивать таймаут только в нужном `location`, а не глобально.
- Приложение с `proxy_pass` на `localhost` в Docker → NGINX в контейнере обращается к самому себе, 502 → указывать имя сервиса из `docker compose`, а не `127.0.0.1`.

## Когда не использовать

На машине разработчика reverse proxy не нужен: `uvicorn --reload` на порту 8000 проще, а заголовки `X-Forwarded-*` только мешают отлаживать. В Kubernetes и за облачным балансировщиком роль входной точки обычно играет ingress-контроллер или шлюз платформы, и NGINX внутри каждого пода оказывается лишним слоем.

Если задача — маршрутизация между микросервисами с авторизацией, лимитами и трассировкой, смотрите в сторону [API Gateway](../../microservices/api_gateway/README.md): там это делается декларативно, а NGINX подойдёт как простой вариант на один-два сервиса.

## Связанные темы

- [Балансировка нагрузки](load_balancing.md) — `upstream` из нескольких экземпляров
- [HTTPS и TLS](tls.md) — приём HTTPS и перенаправление с HTTP
- [Ограничения и безопасность](security.md) — лимиты, таймауты и real IP
- [FastAPI: realtime](../../frameworks/fastapi/realtime.md) — WebSocket и SSE со стороны приложения
