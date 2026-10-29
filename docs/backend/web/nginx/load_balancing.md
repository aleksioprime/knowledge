# Балансировка нагрузки

Группа `upstream` объединяет несколько экземпляров приложения:

```nginx
upstream backend {
    least_conn;

    server 10.0.0.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.0.12:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
    }
}
```

## Алгоритмы

- round-robin — используется по умолчанию и распределяет запросы по очереди;
- `least_conn` — выбирает сервер с меньшим числом активных соединений;
- `ip_hash` — закрепляет клиентский IP за сервером, но хуже переносит изменения состава группы;
- `weight` — задаёт относительную долю трафика для сервера.

Приложение желательно делать stateless: сессии и другие общие данные хранить вне конкретного экземпляра. Тогда запросы можно свободно направлять на любой здоровый сервер.

Пассивные проверки `max_fails` и `fail_timeout` реагируют на ошибки реальных запросов. Возможности активных health checks зависят от редакции NGINX или внешнего балансировщика.
