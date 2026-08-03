# HTTPS и TLS в NGINX

Обычно NGINX принимает HTTPS и перенаправляет обычный HTTP на защищённую версию:

```nginx
server {
    listen 80;
    server_name example.com;
    return 308 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Сертификат должен включать все обслуживаемые имена. Закрытый ключ нельзя добавлять в репозиторий или делать доступным непривилегированным пользователям.

## Практика эксплуатации

- автоматизировать выпуск и продление сертификатов, например через ACME-клиент;
- проверять автоматическое продление и срок действия сертификата;
- использовать актуальную версию NGINX и поддерживаемые версии TLS;
- после изменения выполнять `nginx -t`;
- включать HSTS после проверки HTTPS на всех затрагиваемых доменах;
- при необходимости шифровать и соединение между NGINX и upstream.

Принципы HTTPS и проверки сертификатов описаны в [HTTP: HTTPS и TLS](../http/https_tls.md).
