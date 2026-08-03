# Статика и передача файлов

## Статические файлы

```nginx
server {
    listen 80;
    server_name example.com;

    root /var/www/example;

    location /static/ {
        try_files $uri =404;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

`root` добавляет URI к указанному каталогу. Если используется `alias`, путь подменяется; завершающие слеши у `location` и `alias` должны быть согласованы:

```nginx
location /uploads/ {
    alias /srv/user-files/;
    try_files $uri =404;
}
```

## Ограничение загрузки

```nginx
server {
    client_max_body_size 20m;
    client_body_timeout 30s;

    location /api/uploads {
        proxy_pass http://127.0.0.1:8000;
        proxy_request_buffering off;
        proxy_read_timeout 5m;
    }
}
```

Отключать `proxy_request_buffering` следует только когда приложение действительно обрабатывает поток. Иначе NGINX может сначала принять тело и защитить upstream от медленного клиента.

## Закрытые файлы

Приложение может проверить доступ, а передачу файла поручить NGINX через внутренний location:

```nginx
location /protected-files/ {
    internal;
    alias /srv/protected/;
}
```

После проверки приложение отвечает заголовком `X-Accel-Redirect: /protected-files/report.pdf`. Нельзя формировать такой путь прямо из непроверенного пользовательского ввода.

Подробнее о форматах загрузки, скачивании и диапазонах: [передача файлов по HTTP](../http/file_transfer.md).
