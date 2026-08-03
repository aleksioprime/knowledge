# Защитные HTTP-заголовки

Набор заголовков зависит от приложения. Базовый ориентир:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; object-src 'none'; frame-ancestors 'none'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

- **HSTS** заставляет браузер использовать HTTPS. Не включайте долгий `max-age` и `includeSubDomains`, пока все затронутые домены не готовы.
- **CSP** ограничивает источники скриптов, стилей и других ресурсов. Политику следует адаптировать к приложению и сначала можно проверить в режиме `Content-Security-Policy-Report-Only`.
- **X-Content-Type-Options** запрещает браузеру угадывать MIME-тип вопреки `Content-Type`.
- **Referrer-Policy** управляет информацией, передаваемой в `Referer`.
- **Permissions-Policy** отключает ненужные браузерные возможности.

`X-Frame-Options: DENY` можно оставить для старых клиентов, но современное управление встраиванием выполняет директива CSP `frame-ancestors`.

Защитные заголовки дополняют корректную обработку данных и контроль доступа, но не исправляют уязвимую бизнес-логику.
