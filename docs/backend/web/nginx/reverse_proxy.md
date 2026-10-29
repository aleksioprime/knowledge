# Reverse proxy

Reverse proxy принимает публичный запрос и передаёт его внутреннему приложению. Клиент не подключается к приложению напрямую.

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

## `proxy_pass` и путь

Поведение зависит от завершающего `/`:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
}
```

Здесь запрос `/api/users` уйдёт upstream как `/users`. Без завершающего `/` в `proxy_pass` исходный URI сохраняется. Это различие следует явно проверять для каждой конфигурации.

## WebSocket

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

## SSE и потоковые ответы

Для Server-Sent Events или другого потока часто требуется отключить буферизацию конкретного location:

```nginx
location /events {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_read_timeout 1h;
}
```

Глобально отключать буферизацию без необходимости не стоит: она защищает медленное приложение от медленных клиентов и может повышать пропускную способность.
