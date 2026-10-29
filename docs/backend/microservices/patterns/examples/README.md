# Пример: душитель, предохранительный слой, CQRS и Event Sourcing

Два независимых примера к заметке [Паттерны микросервисной архитектуры](../README.md).

## 1. Душитель и предохранительный слой (Docker Compose)

```text
клиент → gateway (Traefik, :47080) ─┬─ /api/tasks/{id}/comments → monolith или comments
                                    └─ всё остальное           → monolith
comments ── предохранительный слой (app/legacy.py) ──→ monolith (старый формат)
```

- `app/monolith.py` — старый «Задачник»: задачи и комментарии в старом формате (`ttl`, `st` числом, `usr_id`, `txt`, `ts`);
- `app/comments.py` — новый сервис комментариев: новые комментарии хранит у себя, старые читает из монолита;
- `app/legacy.py` — предохранительный слой: переводит старые поля в модель нового сервиса;
- `routes/dynamic.yml` — маршруты шлюза. Traefik следит за папкой и подхватывает правки без перезапуска.

Каждый сервис добавляет к ответу заголовок `X-Served-By`, поэтому видно, кто ответил.

```bash
docker compose -p kb-patterns up -d --build
./check.sh                       # оба пути обслуживает монолит
```

Переключаем комментарии на новый сервис — одна строка в `routes/dynamic.yml`:

```bash
sed -i.bak 's/service: monolith  # переключатель/service: comments  # переключатель/' routes/dynamic.yml && rm routes/dynamic.yml.bak
./check.sh                       # комментарии отвечает comments, задачи — monolith

curl -s -X POST localhost:47080/api/tasks/1/comments \
  -H 'Content-Type: application/json' -d '{"author_id": 11, "text": "Успею к четвергу"}'
```

Откат — та же строка в обратную сторону. Комментарий, созданный в новом сервисе, монолит после отката не увидит: данные новых комментариев живут только в `comments`.

```bash
sed -i.bak 's/service: comments  # переключатель/service: monolith  # переключатель/' routes/dynamic.yml && rm routes/dynamic.yml.bak
docker compose -p kb-patterns down -v --rmi local
```

## 2. CQRS и Event Sourcing (чистый Python, без Docker)

```bash
python3 event_sourcing.py        # Python 3.10+, база SQLite в памяти
```

Журнал событий задачи (`TaskCreated`, `TaskAssigned`, `TaskCompleted`, `TaskReopened`), восстановление состояния, снимки, защита от одновременной записи и проекция «сколько открытых задач у пользователя», которая отстаёт, догоняет и перестраивается с нуля.
