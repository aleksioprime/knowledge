# HTTPS и TLS в NGINX

Приложение на Uvicorn не умеет HTTPS, а без него браузер помечает сайт небезопасным, cookies с флагом `Secure` не работают и пароли идут по сети открытым текстом. Переписывать приложение не нужно: NGINX принимает HTTPS на порту 443, расшифровывает трафик и передаёт приложению обычный HTTP. Это называют TLS termination. Обычно NGINX заодно перенаправляет обычный HTTP на защищённую версию.

## Минимальный пример

Два блока `server`: первый перенаправляет HTTP на HTTPS, второй принимает HTTPS с сертификатом Let's Encrypt:

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
    }
}
```

Проверка: `curl -I http://example.com/tasks` отвечает `308` с `Location: https://example.com/tasks`, а `curl -I https://example.com/tasks` — ответом приложения. Код 308 сохраняет метод и тело запроса, в отличие от 301.

## Как это работает

Клиент устанавливает TLS-соединение с NGINX: проверяет сертификат, договаривается о ключах, и дальше весь трафик между ними зашифрован. NGINX расшифровывает запрос и передаёт приложению по HTTP внутри сервера или частной сети. Приложение узнаёт, что исходный запрос был по HTTPS, из заголовка `X-Forwarded-Proto`:

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

`fullchain.pem` содержит сертификат сайта и промежуточные сертификаты центра — без них часть клиентов не сможет построить цепочку доверия. Сертификат должен включать все обслуживаемые имена. Закрытый ключ нельзя добавлять в репозиторий или делать доступным непривилегированным пользователям.

### Практика эксплуатации

- автоматизировать выпуск и продление сертификатов, например через ACME-клиент;
- проверять автоматическое продление и срок действия сертификата;
- использовать актуальную версию NGINX и поддерживаемые версии TLS;
- после изменения выполнять `nginx -t`;
- включать HSTS после проверки HTTPS на всех затрагиваемых доменах;
- при необходимости шифровать и соединение между NGINX и upstream.

Принципы HTTPS и проверки сертификатов описаны в [HTTP: HTTPS и TLS](../http/https_tls.md).

## Частые ошибки

- Сертификат продлён, а NGINX не перезагружен → процесс держит в памяти старый сертификат, через 90 дней браузеры показывают ошибку истёкшего срока → добавить `nginx -s reload` в хук продления ACME-клиента (`--deploy-hook` у certbot).
- В `ssl_certificate` указан `cert.pem` вместо `fullchain.pem` → в браузере всё работает, а `curl` и мобильные клиенты получают ошибку проверки цепочки → всегда указывать `fullchain.pem`.
- Нет `X-Forwarded-Proto` → приложение считает, что запрос пришёл по HTTP, ставит cookies без `Secure` и строит ссылки `http://` → передавать заголовок и настроить доверие прокси в приложении (`--proxy-headers` у Uvicorn).
- HSTS включён до того, как HTTPS заработал на всех поддоменах → браузеры запоминают правило и отказываются открывать поддомен без HTTPS → включать `Strict-Transport-Security` с малым `max-age`, `includeSubDomains` добавлять после проверки.
- Перенаправление HTTP → HTTPS через 301 для API → клиенты меняют POST на GET при повторе запроса → использовать 308.
- Один `listen 443 ssl` без `server_name` по умолчанию → при обращении по IP или неизвестному домену NGINX отдаёт сертификат первого сайта → добавить `default_server` с `ssl_reject_handshake on`.

## Когда не использовать

Если перед NGINX уже стоит облачный балансировщик или CDN, который завершает TLS, второй раз расшифровывать трафик на NGINX необязательно: достаточно принимать HTTP из частной сети и доверять `X-Forwarded-Proto` от балансировщика. Внутри кластера между сервисами TLS обычно берёт на себя платформа (service mesh), а не NGINX в каждом поде.

Для локальной разработки HTTPS не нужен; если какая-то функция браузера требует защищённого контекста, `localhost` считается безопасным и без сертификата.

## Связанные темы

- [HTTP: HTTPS и TLS](../http/https_tls.md) — рукопожатие, сертификаты и цепочка доверия
- [Reverse proxy](reverse_proxy.md) — заголовки `X-Forwarded-*` и таймауты
- [Защитные HTTP-заголовки](../security/security_headers.md) — HSTS и другие заголовки
- [Установка NGINX](install.md) — структура `/etc/nginx` и первый сайт
