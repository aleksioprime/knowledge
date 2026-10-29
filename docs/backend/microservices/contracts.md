# Контракты между сервисами

Пока «Задачник» — одно приложение, переименовать поле просто: поправил модель, поправил все места, где она используется, тесты зелёные. Когда сервисов несколько, их пишут разные люди и выкатывают в разное время. Сервис задач переименовал `done` в `is_done`, а сервис уведомлений, который читает его события из Kafka, узнаёт об этом в продакшене. **Контракт** — это явное описание формата данных между сервисами: какие поля, каких типов, какие обязательны. Его можно прочитать, проверить в тестах и сравнить со старой версией.

Примеры ниже запущены на Python 3.12.

```bash
pip install jsonschema fastavro
```

## Минимальный пример

Контракт задачи в формате JSON Schema и проверка данных по нему:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://tasker.example.com/schemas/task.json",
  "title": "Task",
  "type": "object",
  "properties": {
    "id": {"type": "integer", "minimum": 1},
    "title": {"type": "string", "minLength": 1, "maxLength": 200},
    "done": {"type": "boolean", "default": false},
    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
    "due_date": {"type": ["string", "null"], "format": "date"},
    "tags": {"type": "array", "items": {"type": "string"}, "uniqueItems": true}
  },
  "required": ["id", "title", "done"],
  "additionalProperties": false
}
```

```python
import json

from jsonschema import Draft202012Validator, FormatChecker

schema = json.load(open('task.schema.json'))
Draft202012Validator.check_schema(schema)  # сама схема написана правильно
validator = Draft202012Validator(schema, format_checker=FormatChecker())

good = {'id': 1, 'title': 'Сдать отчёт', 'done': False, 'priority': 3, 'due_date': '2026-11-01'}
bad = {'id': 0, 'title': '', 'priority': 9, 'due_date': '1 ноября', 'owner': 'anna'}

print(validator.is_valid(good))
for error in sorted(validator.iter_errors(bad), key=lambda e: list(e.path)):
    print(f'{"/".join(map(str, error.path)) or "(корень)"}: {error.message}')
```

```text
True
(корень): 'done' is a required property
(корень): Additional properties are not allowed ('owner' was unexpected)
due_date: '1 ноября' is not a 'date'
id: 0 is less than the minimum of 1
priority: 9 is greater than the maximum of 5
title: '' should be non-empty
```

`iter_errors` собирает все ошибки сразу, а `validate` выбросит исключение на первой. Без `format_checker` поле `format` только описывает данные и не проверяется: `'1 ноября'` прошло бы как дата.

## Code First или Design First

Откуда берётся контракт — два подхода.

**Code First** — сначала код, контракт генерируется из него. FastAPI строит [OpenAPI-схему](../frameworks/fastapi/openapi.md) по моделям Pydantic, DRF — по сериализаторам. Быстро, и схема никогда не расходится с кодом. Но контракт появляется только после того, как код написан, и его форму диктует реализация: переименовали поле в модели — изменили контракт, возможно, не заметив.

**Design First** (его же называют Contract First) — сначала контракт, потом код. Команды обсуждают и согласуют файл `openapi.yaml`, `.proto` или `.avsc`, кладут его в общий репозиторий, а затем каждая пишет свою сторону. Фронтенд и потребители начинают работу сразу, по моку из схемы. Код сервера генерируется из контракта или проверяется на соответствие ему.

| | Code First | Design First |
|---|---|---|
| Что первично | код | файл контракта |
| Скорость старта | быстрее | нужно договориться заранее |
| Расхождение кода и контракта | невозможно | нужны проверки |
| Случайные изменения контракта | легко пропустить | видны в ревью файла контракта |
| Подходит | один сервис и один клиент, внутренние API | публичные API, несколько команд, события в брокере |

На практике их смешивают: HTTP API пишут Code First и защищают [тестом на изменение `openapi.json`](../frameworks/fastapi/openapi.md#проверка-в-ci-схема-не-изменилась-незаметно), а для gRPC и событий в Kafka контракт пишут первым, потому что без `.proto` или `.avsc` код просто не собрать.

## Форматы контрактов

| Формат | Для чего | Данные |
|---|---|---|
| JSON Schema | JSON-документы: тела запросов, сообщения, конфиги | JSON, текст |
| OpenAPI | HTTP API целиком: пути, методы, коды ответов, схемы тел | JSON; схемы тел — диалект JSON Schema |
| Protobuf | gRPC и бинарные сообщения | бинарные, поля по номерам |
| Avro | события в Kafka, большие объёмы данных | бинарные, поля по порядку из схемы |

**JSON Schema** — показана выше. Хороша тем, что проверяет обычный JSON, который уже ходит между сервисами, и не требует менять формат обмена. Минусы: данные остаются текстовыми и большими, а правила совместимости приходится соблюдать вручную.

**OpenAPI** описывает весь HTTP API и включает JSON Schema для тел. Как получить его из FastAPI, выгрузить в файл и проверять в CI — в заметке [Документация API](../frameworks/fastapi/openapi.md).

**Protobuf** — контракт для gRPC: файл `.proto`, из которого генерируется код. В сообщении передаются номера полей, а не имена, поэтому имя можно менять, а номер — никогда. Подробно — в разделе [gRPC](../web/http/api_design.md#grpc) и [примере](../web/http/examples/grpc/README.md).

### Avro

Avro — бинарный формат, который чаще всего встречается в Kafka. Схема — обычный JSON:

```python
from fastavro import parse_schema

v1 = parse_schema({
    'type': 'record', 'name': 'TaskCreated', 'namespace': 'tasker.events',
    'fields': [
        {'name': 'id', 'type': 'long'},
        {'name': 'title', 'type': 'string'},
        {'name': 'done', 'type': 'boolean', 'default': False},
    ],
})
```

В отличие от Protobuf, в данных нет ни имён, ни номеров полей, только значения подряд в порядке схемы. Отсюда компактность и главная особенность: **без схемы писателя данные не прочитать**.

```python
import io
import json

from fastavro import schemaless_reader, schemaless_writer


def encode(record: dict, schema) -> bytes:
    buffer = io.BytesIO()
    schemaless_writer(buffer, schema, record)
    return buffer.getvalue()


def decode(data: bytes, writer_schema, reader_schema) -> dict:
    return schemaless_reader(io.BytesIO(data), writer_schema, reader_schema)


old_event = encode({'id': 7, 'title': 'Сдать отчёт', 'done': False}, v1)
print(len(old_event), len(json.dumps({'id': 7, 'title': 'Сдать отчёт', 'done': False}, ensure_ascii=False).encode()))
# 24 58
print(old_event)
# b'\x0e*\xd0\xa1\xd0\xb4\xd0\xb0\xd1\x82\xd1\x8c \xd0\xbe\xd1\x82\xd1\x87\xd1\x91\xd1\x82\x00'
#   ^id=7 ^длина 21  ^байты строки «Сдать отчёт»                                    ^done=False
```

24 байта против 58 у JSON. Числа записаны в формате zigzag varint: `7` → `\x0e`, `21` → `*` (`0x2a`).

**Эволюция схемы.** При чтении Avro сопоставляет две схемы: ту, которой данные записаны (writer), и ту, которую ждёт читатель (reader). Поля сопоставляются по имени. Чего нет у писателя, читатель берёт из `default`. Чего нет у читателя, пропускается.

```python
v2 = parse_schema({
    'type': 'record', 'name': 'TaskCreated', 'namespace': 'tasker.events',
    'fields': [
        {'name': 'id', 'type': 'long'},
        {'name': 'title', 'type': 'string'},
        {'name': 'done', 'type': 'boolean', 'default': False},
        {'name': 'priority', 'type': 'int', 'default': 1},
        {'name': 'due_date', 'type': ['null', {'type': 'int', 'logicalType': 'date'}], 'default': None},
    ],
})

# новый потребитель читает старое сообщение: недостающие поля берутся из default
print(decode(old_event, v1, v2))
# {'id': 7, 'title': 'Сдать отчёт', 'done': False, 'priority': 1, 'due_date': None}

# старый потребитель читает новое сообщение: лишние поля пропускаются
new_event = encode({'id': 8, 'title': 'Купить хлеб', 'done': True, 'priority': 3, 'due_date': None}, v2)
print(decode(new_event, v2, v1))
# {'id': 8, 'title': 'Купить хлеб', 'done': True}
```

Необязательное поле в Avro — объединение (union) с `null` первым и `default: None`. Новое поле без `default` ломает чтение старых данных:

```python
v3_broken = parse_schema({
    'type': 'record', 'name': 'TaskCreated', 'namespace': 'tasker.events',
    'fields': [
        {'name': 'id', 'type': 'long'},
        {'name': 'title', 'type': 'string'},
        {'name': 'owner_id', 'type': 'long'},  # новое поле без default
    ],
})
decode(old_event, v1, v3_broken)
# SchemaResolutionError: No default value for field owner_id in tasker.events.TaskCreated
```

Раз нужна схема писателя, её где-то надо брать. В файлах Avro (`fastavro.writer`) схема записывается в заголовок файла. В Kafka на каждое сообщение схему не положишь — для этого есть Schema Registry.

## Совместимость

Изменение контракта оценивают с двух сторон:

- **обратная совместимость (backward)** — **новый** читатель понимает **старые** данные. Нужна, когда сначала обновляют потребителей: они должны дочитать то, что лежит в топике;
- **прямая совместимость (forward)** — **старый** читатель понимает **новые** данные. Нужна, когда сначала обновляют производителя, а потребители переходят позже;
- **полная (full)** — и то и другое: порядок выкатки не важен.

Что получилось на Avro (`fastavro`, старая и новая схема, запись одной и чтение другой):

| Изменение | Backward | Forward | Итог |
|---|---|---|---|
| Добавить поле с `default` | да | да | full |
| Добавить поле без `default` | нет | да | только forward |
| Удалить поле, у которого был `default` | да | да | full |
| Удалить поле без `default` | да | нет | только backward |
| Переименовать поле | нет | нет | ломает |
| Переименовать с `aliases: ["старое имя"]` | да | нет | только backward |
| `int` → `long` | да | нет | только backward |
| `long` → `int` | нет | да | только forward |
| Новое значение `enum` | да | нет, если у `enum` нет `default` | backward; full с `default` |

Отсюда практическое правило: **добавляйте и удаляйте только поля с `default`**, тогда изменение полностью совместимо. Переименование — это добавление нового поля и, позже, удаление старого, когда его никто не читает.

Для JSON и JSON Schema логика та же, но проверяет её не библиотека, а дисциплина: потребители игнорируют незнакомые поля, а производитель не удаляет обязательные. В схеме это `additionalProperties`: строгое `false` на стороне потребителя делает любое новое поле ломающим. Поэтому строгие схемы держат для входных данных своего сервиса, а для чужих ответов перечисляют только нужные поля. Те же правила для HTTP API — в разделе [Обратная совместимость](../web/http/api_design.md#обратная-совместимость), для Protobuf — в [номерах полей](../web/http/api_design.md#номера-полей-важнее-имён).

## Schema Registry

Schema Registry — отдельный сервис рядом с [Kafka](broker/kafka/README.md), который хранит версии схем для каждого топика (точнее, для «субъекта», обычно `<топик>-value`).

1. Производитель перед отправкой регистрирует схему (или находит уже зарегистрированную) и получает её числовой id.
2. В сообщение кладётся маленький заголовок с id схемы и данные Avro, Protobuf или JSON.
3. Потребитель по id получает схему писателя из реестра (и кэширует её) и читает данные своей схемой.

Главное — проверка совместимости **при регистрации**. Для субъекта задаётся режим (`BACKWARD` по умолчанию в Confluent Schema Registry, `FORWARD`, `FULL`, их `_TRANSITIVE`-варианты — проверка против всех прошлых версий, а не только последней, или `NONE`). Схема, нарушающая режим, просто не зарегистрируется, и производитель с ней не запустится. Ломающее изменение не дойдёт до топика.

Популярные реализации: Confluent Schema Registry, Karapace (совместимый открытый аналог), Apicurio Registry. В Python с реестром работает `confluent-kafka` (`confluent_kafka.schema_registry`).

## Контрактные тесты

Схема в репозитории сама ничего не гарантирует. Её проверяют тестами.

**Простая проверка в CI для Avro** — прочитать данные, записанные каждой версией схемы, следующей версией и наоборот:

```python
# tests/test_avro_compat.py
import io
import json
from pathlib import Path

import pytest
from fastavro import parse_schema, schemaless_reader, schemaless_writer
from fastavro.utils import generate_many

SCHEMAS = sorted(Path('schemas/task_created').glob('v*.avsc'), key=lambda p: int(p.stem[1:]))


def load(path: Path):
    return parse_schema(json.loads(path.read_text()))


@pytest.mark.parametrize('old_path, new_path', list(zip(SCHEMAS, SCHEMAS[1:])))
def test_full_compatibility(old_path, new_path):
    old, new = load(old_path), load(new_path)
    for writer, reader in [(old, new), (new, old)]:  # backward и forward
        for record in generate_many(writer, 20):  # случайные записи по схеме
            buffer = io.BytesIO()
            schemaless_writer(buffer, writer, record)
            buffer.seek(0)
            schemaless_reader(buffer, writer, reader)
```

С файлами `v1.avsc` и `v2.avsc` (добавлено `priority` с `default`) тест проходит. Добавили `v3.avsc` с обязательным `owner_id` — падает:

```text
E   fastavro._read_common.SchemaResolutionError: No default value for field owner_id in tasker.events.TaskCreated
1 failed, 1 passed in 0.04s
```

Тест на случайных данных ловит не всё. Новое значение `enum` он пропустил: генератор ни разу не выдал это значение, а старый читатель падает только на нём (`archived not found in reader symbol list S`). Надёжнее проверка схем самим Schema Registry: у него есть HTTP-эндпоинт `POST /compatibility/subjects/{subject}/versions/latest`, который сравнивает схемы, а не данные.

**Проверка ответа по схеме потребителя.** Django-админка, которая [входит через Auth-сервис](../frameworks/django/auth.md#вход-в-админку-через-auth-сервис), использует из ответа `GET /auth/me` три поля. Это ожидание записано в схему, и **Auth-сервис** проверяет его в своих тестах:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Что Django-админка ждёт от GET /auth/me",
  "type": "object",
  "properties": {
    "id": {"type": "integer"},
    "email": {"type": "string"},
    "roles": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["id", "email", "roles"]
}
```

```python
# tests/integration/test_contracts.py
async def test_me_matches_django_admin_contract(client, make_user, login):
    await make_user('anna@example.com')
    tokens = await login('anna@example.com')

    response = await client.get('/auth/me', headers=bearer(tokens))

    schema = json.loads((CONTRACTS / 'django_admin.auth_me.schema.json').read_text())
    Draft202012Validator(schema).validate(response.json())
```

`additionalProperties` здесь не запрещены: Auth-сервис может добавлять поля, не спрашивая админку. Если в Auth-сервисе переименовать `roles` в `role_names`, тест упадёт раньше, чем админка перестанет пускать менеджеров:

```text
E           jsonschema.exceptions.ValidationError: 'roles' is a required property
1 failed in 0.44s
```

Полный код — в [примере Auth-сервиса](../frameworks/fastapi/examples/auth_service/README.md).

### Pact и consumer-driven contracts

Пример выше — упрощённая версия идеи **контрактов, управляемых потребителем** (consumer-driven contracts). Контракт пишет не тот, кто отдаёт данные, а тот, кто их использует: «я вызываю `GET /auth/me` и жду `id`, `email` и `roles`». Поставщику достаточно выполнить ожидания всех потребителей, а всё, чем никто не пользуется, он может менять свободно.

**Pact** автоматизирует этот процесс:

1. Тесты потребителя работают против мок-сервера Pact и описывают взаимодействия: запрос и ожидаемый ответ. По итогам создаётся файл контракта (pact).
2. Файл публикуется в Pact Broker.
3. CI поставщика скачивает контракты всех потребителей и прогоняет их против настоящего сервиса.
4. Перед выкаткой `can-i-deploy` спрашивает у брокера, совместима ли эта версия с версиями потребителей в продакшене.

Pact оправдан, когда потребителей несколько и они в разных репозиториях. Для двух сервисов одной команды хватает схемы потребителя в репозитории поставщика, как выше.

## Частые ошибки

- **Контракт только в голове или в вики.** Описание в Confluence устаревает в день написания. Контракт должен быть файлом, который проверяют тесты или реестр.
- **Строгая схема на чужих данных.** `additionalProperties: false` для ответа другого сервиса превращает любое добавленное им поле в аварию. Проверяйте только то, что используете.
- **Новое поле в Avro без `default`.** Новые потребители не прочитают сообщения, которые уже лежат в топике. Добавляйте поля с `default`, необязательные — как `["null", тип]` с `default: null`.
- **Переименование поля одним изменением.** И в JSON, и в Avro это удаление плюс добавление. Делайте в два этапа: добавить новое и писать оба, перевести потребителей, удалить старое.
- **Переиспользовать номер поля Protobuf.** Старые сообщения прочитаются с чужими данными в новом поле. Помечайте удалённые номера `reserved`.
- **Проверять совместимость только с последней версией.** В топике могут лежать сообщения трёх версий назад. Для долгоживущих топиков нужен режим `*_TRANSITIVE`.

## Когда не использовать

Формальный контракт с реестром и контрактными тестами избыточен, когда поставщик и потребитель живут в одном репозитории и выкатываются вместе: обычные интеграционные тесты увидят поломку. Не нужен Avro и там, где сообщений немного, а людям важно читать их глазами: JSON с JSON Schema проще отлаживать.

## Связанные темы

- [Проектирование API: REST, версионирование, gRPC](../web/http/api_design.md)
- [Документация API в FastAPI](../frameworks/fastapi/openapi.md) — OpenAPI и проверка схемы в CI
- [Kafka](broker/kafka/README.md) — брокер, где чаще всего нужен реестр схем
- [Сессии на JWT: refresh, выход, роли](../frameworks/fastapi/auth_sessions.md) — Auth-сервис с контрактным тестом
