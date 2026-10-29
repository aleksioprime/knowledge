# Кластер Kafka из трёх брокеров

Стенд для опытов с репликацией, `acks`, `min.insync.replicas`, компакцией и лагом потребителей. Объяснение — в заметке [Kafka изнутри](../../docs/internals.md).

| Сервис | Роль | Порт на хосте |
|---|---|---|
| `controller` | контроллер KRaft (node id 1) | — |
| `kafka-1` | брокер 101 | `39092` |
| `kafka-2` | брокер 102 | `39093` |
| `kafka-3` | брокер 103 | `39094` |

Образ — официальный `apache/kafka:4.1.0`. Образы Bitnami для Kafka больше не обновляются в бесплатном каталоге, поэтому берём образ проекта Apache. Контроллер вынесен в отдельный контейнер, чтобы останавливать брокеры, не ломая кворум метаданных; в продакшене контроллеров три. Настройки по умолчанию для новых топиков: `replication.factor=3`, `min.insync.replicas=2`, автосоздание топиков выключено. Куча JVM ограничена 256 МБ на брокер, весь кластер занимает около 1,2 ГБ памяти.

## Запуск

```bash
docker compose -p kb-kafka up -d
docker compose -p kb-kafka ps    # ждём (healthy) у трёх брокеров

alias kt='docker compose -p kb-kafka exec kafka-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092'
kt --create --topic task-events --partitions 3
kt --describe --topic task-events
```

## Опыт: что пишется при отказах

Скрипт `produce.py` шлёт события с ключом `user-1` с выбранным `acks` (клиент `aiokafka`, подключается к `kafka-1`):

```bash
uv run --with aiokafka==0.15.0 produce.py --acks all --count 2

docker compose -p kb-kafka stop kafka-3
uv run --with aiokafka==0.15.0 produce.py --acks all --count 2   # записано: в ISR два брокера

docker compose -p kb-kafka stop kafka-2
uv run --with aiokafka==0.15.0 produce.py --acks all --count 2   # NotEnoughReplicasError
uv run --with aiokafka==0.15.0 produce.py --acks 1 --count 2     # записано, но не видно потребителям

# Лидер падает, вместо него поднимается kafka-2
docker compose -p kb-kafka stop kafka-1
docker compose -p kb-kafka start kafka-2
docker compose -p kb-kafka exec kafka-2 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --describe --topic task-events

docker compose -p kb-kafka start kafka-1 kafka-3
docker compose -p kb-kafka logs kafka-1 | grep Truncating   # записанное с acks=1 обрезано
```

Пока `kafka-1` остановлен, `produce.py` к нему не подключится: поменяйте `BOOTSTRAP` на `127.0.0.1:39093`.

## Сегменты на диске

```bash
docker compose -p kb-kafka exec kafka-1 ls -la /var/lib/kafka/data/task-events-2
docker compose -p kb-kafka exec kafka-1 /opt/kafka/bin/kafka-dump-log.sh --print-data-log \
  --files /var/lib/kafka/data/task-events-2/00000000000000000000.log
```

## Компакция

```bash
kt --create --topic task-status --partitions 1 \
  --config cleanup.policy=compact --config segment.ms=5000 --config min.cleanable.dirty.ratio=0.01

printf 'task-1:new\ntask-2:new\ntask-1:in_progress\ntask-3:new\ntask-1:done\ntask-2:done\n' | \
  docker compose -p kb-kafka exec -T kafka-1 /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic task-status --property parse.key=true --property key.separator=:

# Через несколько секунд ещё одно сообщение, чтобы первый сегмент закрылся
printf 'task-4:new\n' | docker compose -p kb-kafka exec -T kafka-1 /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic task-status --property parse.key=true --property key.separator=:

# Через полминуты в закрытом сегменте останется последнее значение каждого ключа
docker compose -p kb-kafka exec kafka-1 /opt/kafka/bin/kafka-dump-log.sh --print-data-log \
  --files /var/lib/kafka/data/task-status-0/00000000000000000000.log
```

Компакцию делает реплика на каждом брокере сама; если `kafka-1` не лидер партиции, результат тот же.

## Лаг потребителя

```bash
docker compose -p kb-kafka exec kafka-1 /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic task-events --group stats --from-beginning --max-messages 4

docker compose -p kb-kafka exec kafka-1 /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group stats
```

## Удаление

```bash
docker compose -p kb-kafka down -v
```
