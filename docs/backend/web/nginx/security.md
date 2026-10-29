# Ограничения и безопасность NGINX

NGINX может отбрасывать часть нежелательного трафика до приложения, но не заменяет проверку доступа и входных данных в самом приложении.

## Ограничение частоты

Зона объявляется в контексте `http`, а правило применяется в `server` или `location`:

```nginx
limit_req_zone $binary_remote_addr zone=api_per_ip:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=connections_per_ip:10m;

server {
    location /api/ {
        limit_req zone=api_per_ip burst=20 nodelay;
        limit_conn connections_per_ip 20;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Если NGINX находится за доверенным балансировщиком, сначала необходимо корректно настроить real IP. Иначе все запросы будут выглядеть пришедшими с одного адреса либо клиент сможет подделать адрес.

## Границы запроса

```nginx
client_max_body_size 20m;
client_body_timeout 15s;
client_header_timeout 15s;
keepalive_timeout 30s;
send_timeout 30s;
```

Значения подбираются под реальные клиенты и размеры данных. Слишком строгие лимиты нарушат медленные загрузки, слишком мягкие увеличат стоимость атаки.

## Защитные заголовки

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

CSP и CORS лучше задавать там, где известна семантика ответа. Избыточные или дублирующиеся заголовки от приложения и NGINX могут дать неожиданный результат. Подробнее: [защитные HTTP-заголовки](../security/security_headers.md).

## Дополнительные меры

- принимать только известные `server_name` и добавить отдельный default server для неизвестных доменов;
- скрывать служебные endpoints и не публиковать внутренние порты приложений;
- ограничивать методы там, где набор действительно фиксирован;
- регулярно обновлять NGINX и TLS-библиотеки;
- анализировать access/error logs, не записывая токены и другие секреты;
- использовать внешний DDoS-фильтр, если атака способна заполнить сетевой канал.
