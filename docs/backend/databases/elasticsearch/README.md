# Elasticsearch

**Elasticsearch** — распределённый поисковый и аналитический движок на базе Apache Lucene. Используется для полнотекстового поиска с учётом морфологии и опечаток, а также как хранилище логов и аналитики (связка ELK: Elasticsearch + Logstash + Kibana).

## Содержание

- [Полнотекстовый поиск](search.md) — индексы и маппинги, анализаторы, `text` и `keyword`, `match`, `fuzziness`, `bool`, подсветка, агрегации
- [ETL из PostgreSQL](etl.md) — загрузка изменений пачками, курсор по `(modified, id)`, сборка документа из нескольких таблиц, состояние, `backoff`, bulk ([пример](examples/etl/README.md))

## Связанные темы

- [Централизованное логирование](../../../infrastructure/monitoring/logging/README.md)
- [MongoDB](../mongodb/README.md)
