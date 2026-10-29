# API Gateway

Когда сервисов несколько, фронтенду неудобно знать адрес каждого: задачи на одном порту, пользователи на другом, уведомления на третьем. И в каждом сервисе пришлось бы повторять одно и то же: TLS, ограничение частоты запросов, логирование, CORS. **API Gateway** — единая точка входа: клиент ходит только на него, а шлюз по пути запроса решает, в какой сервис его отправить, и по дороге делает общую для всех работу.

Пример — в папке [example](examples/): шлюз Traefik перед двумя сервисами. Вместо настоящих сервисов используется `traefik/whoami` — он просто возвращает, какой запрос получил.

```bash
cd example
docker compose up -d
```

## Минимальный пример

```bash
curl localhost:8090/api/users/42
```

```text
Name: users
Hostname: 10f81fea6fde
GET /42 HTTP/1.1
X-Forwarded-For: 192.168.65.1
X-Forwarded-Prefix: /api/users
X-Real-Ip: 192.168.65.1
```

Клиент обратился к шлюзу по пути `/api/users/42`, а сервис `users` получил `GET /42`: шлюз выбрал сервис по префиксу, отрезал префикс и добавил заголовки с адресом настоящего клиента.

```bash
curl localhost:8090/api/billing
# 404 page not found — такого маршрута нет
```

## Как это работает

Traefik читает настройки из меток (labels) контейнеров. Он подключается к Docker и сам видит, какие сервисы запущены. Добавили сервис с метками — маршрут появился без перезапуска шлюза.

```yaml
# example/docker-compose.yaml
tasks:
  image: traefik/whoami:v1.10
  deploy:
    replicas: 2
  labels:
    - traefik.enable=true
    - traefik.http.routers.tasks.rule=PathPrefix(`/api/tasks`)
    - traefik.http.routers.tasks.middlewares=tasks-strip,tasks-ratelimit
    - traefik.http.middlewares.tasks-strip.stripprefix.prefixes=/api/tasks
    - traefik.http.middlewares.tasks-ratelimit.ratelimit.average=5
    - traefik.http.middlewares.tasks-ratelimit.ratelimit.burst=10
```

Три понятия Traefik:

- **router** — правило, какие запросы куда отправлять: по пути, домену, заголовкам;
- **middleware** — обработка по дороге: отрезать префикс, ограничить частоту, проверить авторизацию, добавить заголовки;
- **service** — куда отправить запрос в итоге. Если копий сервиса несколько, Traefik распределяет запросы между ними.

## Балансировка

У сервиса `tasks` две копии, и запросы идут к ним по очереди:

```bash
for i in 1 2 3 4; do curl -s localhost:8090/api/tasks/ | grep Hostname; done
# Hostname: 6a3bcff7af3a
# Hostname: 35c880eaf924
# Hostname: 6a3bcff7af3a
# Hostname: 35c880eaf924
```

## Ограничение частоты запросов

`average=5` — в среднем 5 запросов в секунду, `burst=10` — можно разово превысить на 10. Отправим 15 запросов подряд:

```bash
for i in $(seq 1 15); do curl -s -o /dev/null -w '%{http_code} ' localhost:8090/api/tasks/; done
# 200 200 200 200 200 200 200 200 200 200 200 429 429 429 429
```

```text
HTTP/1.1 429 Too Many Requests
Retry-After: 1
```

Шлюз ответил сам, и лишние запросы до сервиса не дошли. Лимит считается по IP клиента и для каждого маршрута свой: на `/api/users` ограничения нет.

## Что ещё обычно делает шлюз

- **TLS**: принимает HTTPS и сам получает сертификаты Let's Encrypt, а внутри системы трафик идёт по HTTP;
- **проверка авторизации**: middleware `forwardAuth` отправляет заголовки запроса в сервис авторизации и пропускает запрос дальше, только если тот ответил 200. Так проверку токена [Keycloak](../keycloak/README.md) можно сделать один раз на входе;
- **CORS, сжатие, повторы, таймауты, логи доступа и метрики** — одинаково для всех сервисов.

Панель Traefik со всеми маршрутами: http://localhost:8091.

## Traefik, NGINX или что-то ещё

[NGINX](../../web/nginx/reverse_proxy.md) тоже работает как шлюз, но маршруты описываются в файле конфигурации, и после изменения его нужно перезагрузить. Traefik удобен в Docker и Kubernetes: маршруты появляются сами вместе с сервисами. Kong, KrakenD, Envoy и облачные шлюзы (AWS API Gateway, Yandex API Gateway) добавляют плагины, управление ключами API и аналитику.

## Частые ошибки

- **Шлюз не видит Docker.** В логах `Failed to retrieve information of the docker client and server host error="Error response from daemon: "`. Так ведут себя старые версии Traefik (например, v3.2) с Docker Engine 29 и новее: изменилась минимальная версия API Docker. Обновите Traefik — пример проверен на v3.6.
- **Забытый `stripprefix`.** Сервис получит `/api/tasks/42` вместо `/tasks/42` и ответит 404. Либо отрезайте префикс на шлюзе, либо научите сервис работать с ним (`root_path` в FastAPI).
- **Сервис доступен в обход шлюза.** Если у сервиса опубликован порт наружу, ограничения и проверки шлюза можно обойти. Наружу открывают только шлюз.
- **Бизнес-логика в шлюзе.** Шлюз должен маршрутизировать и делать общую техническую работу. Правила вроде «пользователь видит только свои задачи» — дело сервиса.
- **Один шлюз без запаса.** Если шлюз упал, недоступна вся система. В продакшене запускают несколько копий.

## Связанные темы

- [NGINX как обратный прокси](../../web/nginx/reverse_proxy.md)
- [Балансировка в NGINX](../../web/nginx/load_balancing.md)
- [Rate limiting на Redis](../../databases/redis/scenarios.md#3-ограничение-частоты-запросов-rate-limiting) — ограничение внутри приложения
- [Keycloak](../keycloak/README.md)
