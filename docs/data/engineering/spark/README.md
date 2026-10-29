# Apache Spark и обработка больших данных

Журнал событий «Задачника» вырос до миллиардов строк и сотен гигабайт. Посчитать по нему отчёт на одной машине не выходит: данные не помещаются ни в память, ни на один диск, а прочитать терабайт с одного диска — это часы. Остаётся разложить данные по многим машинам и заставить каждую считать свою часть. **Apache Spark** — движок, который берёт на себя эту раздачу: вы описываете вычисление как над одной таблицей, а Spark сам делит его на задачи, отправляет на узлы кластера, собирает результаты и перезапускает упавшие куски.

## Минимальный пример

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.master('local[2]').getOrCreate()

events = spark.read.csv('data/events.csv', header=True, inferSchema=True)
(events
    .groupBy('event_type')
    .agg(F.count('*').alias('events'), F.round(F.avg('duration_ms')).alias('avg_ms'))
    .orderBy(F.desc('events'))
    .show())
```

```text
+--------------+-------+------+
|    event_type| events|avg_ms|
+--------------+-------+------+
|status_changed|1200836| 799.0|
|     commented| 899783| 800.0|
|         rated| 448762| 798.0|
|      assigned| 150870| 800.0|
|       created| 150213| 801.0|
|        closed| 149536| 800.0|
+--------------+-------+------+
```

`local[2]` — запустить всё в одном процессе на двух ядрах. На кластере меняется только адрес мастера (`spark://...`, `yarn`, `k8s://...`), код остаётся тем же.

## Как это работает

### Откуда всё взялось

Spark — третье поколение идей, которые Google описал в статьях начала 2000-х.

**GFS (2003) → HDFS.** Распределённая файловая система: файл режется на блоки по 64–128 МБ, каждый блок хранится на трёх машинах. Один узел-координатор (NameNode в HDFS) помнит, где какой блок. Обычные дешёвые серверы ломаются постоянно, а данные не теряются. Hadoop Distributed File System — открытая реализация той же идеи.

**MapReduce (2004).** Модель вычислений поверх такой файловой системы. Главная мысль: не тащить данные к программе, а отправлять программу к данным — туда, где лежат блоки. Вычисление описывается двумя функциями:

- **map** — каждый узел независимо превращает свои записи в пары «ключ → значение»;
- **shuffle** — фреймворк собирает пары с одинаковым ключом на одном узле. Это единственный шаг, где данные едут по сети;
- **reduce** — каждый узел сворачивает значения своих ключей.

Подсчёт слов в комментариях — «hello world» этой модели ([examples/wordcount_mapreduce.py](examples/wordcount_mapreduce.py)):

```python
from collections import defaultdict
from itertools import chain

splits = [  # куски данных на трёх узлах
    ['Починить кран на кухне', 'Купить хлеб и молоко'],
    ['Починить велосипед', 'Сдать отчёт до пятницы'],
    ['Купить подарок', 'Починить кран в ванной'],
]


def map_phase(lines):
    return [(word.lower(), 1) for line in lines for word in line.split()]


def shuffle_phase(mapped, reducers):
    buckets = [defaultdict(list) for _ in range(reducers)]
    for word, count in chain.from_iterable(mapped):
        buckets[hash(word) % reducers][word].append(count)  # один ключ — всегда один reducer
    return buckets


def reduce_phase(bucket):
    return {word: sum(counts) for word, counts in bucket.items()}


mapped = [map_phase(split) for split in splits]  # параллельно на 3 узлах
result = {}
for bucket in shuffle_phase(mapped, reducers=2):  # параллельно на 2 узлах
    result.update(reduce_phase(bucket))

sorted(result.items(), key=lambda item: (-item[1], item[0]))[:4]
# [('починить', 3), ('кран', 2), ('купить', 2), ('в', 1)]
```

Модель проста и отказоустойчива: упал узел — его кусок map или reduce просто перезапускают. Но каждый шаг пишет промежуточный результат на диск в HDFS, а реальный отчёт — это цепочка из десятка MapReduce-заданий. Итеративные алгоритмы (машинное обучение, графы) работали мучительно медленно.

**BigTable (2006) → HBase, Cassandra.** Распределённая таблица «ключ → колонки» поверх GFS для точечных чтений и записей — то, чего MapReduce не умеет. Внутри — [LSM-дерево](../../../backend/databases/storage/README.md#lsm-дерево-только-дописывать): memtable, SSTable, компакция. Открытые наследники — HBase, частично Cassandra.

**Spark (2009, Беркли; Apache с 2013).** Та же идея «программа к данным», но промежуточные результаты по возможности держатся в памяти, а вместо пары map/reduce — целый граф операций, который оптимизируется целиком. На многошаговых задачах это быстрее MapReduce в разы, а на итеративных — на порядки.

### Как устроен Spark

```text
  драйвер (ваша программа, SparkSession)
     │  строит план, делит его на стадии и задачи
     ▼
  менеджер кластера (standalone, YARN, Kubernetes)
     │  выделяет ресурсы
     ▼
  экзекьюторы — процессы на узлах; каждый выполняет задачи над своими партициями
```

- **Драйвер** (driver) — процесс, где работает ваш код. Он не обрабатывает данные сам, а строит план и раздаёт задачи. Результат `collect()` тоже приезжает в драйвер — отсюда классическое падение по памяти, если «собрать» миллиард строк.
- **Экзекьюторы** (executors) — рабочие процессы на узлах кластера. Каждое ядро экзекьютора одновременно выполняет одну задачу.
- **Партиция** (partition) — кусок данных, который обрабатывает одна задача. Число партиций определяет параллелизм: 2 партиции на 100 ядрах — 98 ядер простаивают.

В локальном режиме (`local[N]`) драйвер и экзекьютор — один JVM-процесс, а N — число потоков-«ядер».

#### RDD и DataFrame

**RDD** (Resilient Distributed Dataset) — исходная абстракция: распределённая коллекция произвольных объектов и функции над ними (`map`, `filter`, `reduceByKey`). Spark не знает, что внутри объектов и функций, поэтому оптимизировать не может, а в PySpark каждая лямбда ещё и гоняет данные между JVM и Python.

**DataFrame** — таблица с именованными колонками и типами. Операции описываются выражениями (`F.col('event_type') == 'closed'`), и оптимизатор Catalyst видит весь запрос: выбрасывает ненужные колонки, проталкивает фильтры к источнику, выбирает тип соединения. Выполнение — в JVM, без Python. Для нового кода — только DataFrame и Spark SQL; RDD остаётся для редких низкоуровневых задач.

#### Ленивость: трансформации и действия

Операции делятся на два вида:

- **трансформации** (transformations) — `select`, `filter`, `groupBy`, `join`, `withColumn`. Они ничего не считают, а только достраивают план;
- **действия** (actions) — `count`, `collect`, `show`, `write`. Только они запускают вычисление.

```python
events = spark.read.csv('/data/events.csv', header=True, schema=events_schema)
closed = events.filter(F.col('event_type') == 'closed').select('task_id', 'ts')
# план построен, данных ещё не читали
closed.count()
# 149536 — только здесь Spark прочитал 165 МБ CSV (13,7 с)
```

Ленивость позволяет оптимизатору увидеть всю цепочку сразу. Обратная сторона: каждое действие заново выполняет план с самого начала. Если один и тот же промежуточный DataFrame нужен нескольким действиям, его кэшируют (`df.cache()`).

#### Shuffle и почему он дорогой

Узкие (narrow) трансформации — `filter`, `select`, `withColumn` — работают с каждой партицией независимо. **Широкие** (wide) — `groupBy`, `join`, `orderBy`, `distinct` — требуют собрать строки с одинаковым ключом в одном месте. Это и есть shuffle из MapReduce: каждая задача раскладывает свои строки по корзинам, пишет их на локальный диск, а задачи следующей стадии скачивают свои корзины по сети со всех узлов.

Shuffle дорогой трижды: сериализация, запись на диск и передача по сети, причём каждый с каждым. На нём же Spark режет план на **стадии** (stages): стадия не может начаться, пока предыдущая не записала все корзины. В плане запроса shuffle виден как `Exchange`.

Как уменьшить shuffle:

- фильтровать и отбрасывать колонки **до** `groupBy`/`join`;
- маленькую таблицу соединять через **broadcast join**: её целиком рассылают всем экзекьюторам, а большую не перемешивают. Spark делает это сам для таблиц меньше `spark.sql.autoBroadcastJoinThreshold` (10 МБ);
- следить за перекосом (skew): если у одного ключа половина строк, одна задача будет работать час, пока остальные ждут.

`spark.sql.shuffle.partitions` (по умолчанию 200) задаёт число партиций после shuffle. Для маленьких данных это много крошечных задач, для терабайтов — мало. Adaptive Query Execution (включён по умолчанию с Spark 3.2) сам объединяет мелкие партиции и делит перекошенные.

### PySpark на практике

Пример [examples/task_stats.py](examples/task_stats.py) считает статистику по журналу из 3 миллионов событий и справочнику из 150 тысяч задач. Данные генерирует [examples/generate_events.py](examples/generate_events.py).

#### Запуск

Spark работает на JVM, поэтому нужна Java 17 или 21. Проще всего взять официальный образ, где уже есть Java, Spark и Python:

```bash
cd docs/data/engineering/spark/examples
mkdir -p data
docker run --rm -v "$PWD":/app -w /app spark:4.1.3-python3 python3 generate_events.py data 3000000
docker run --rm -v "$PWD":/app -w /app spark:4.1.3-python3 \
    /opt/spark/bin/spark-submit --master 'local[2]' --driver-memory 512m task_stats.py data /tmp/out
```

Без Docker — `pip install pyspark==4.1.3` и установленный JDK.

#### Чтение: схема, CSV и Parquet

```python
events_schema = StructType([
    StructField('event_id', LongType()),
    StructField('task_id', IntegerType()),
    StructField('user_id', IntegerType()),
    StructField('event_type', StringType()),
    StructField('ts', TimestampType()),
    StructField('duration_ms', IntegerType()),
])
events_csv = spark.read.csv('data/events.csv', header=True, schema=events_schema)
events_csv.write.mode('overwrite').parquet('out/events.parquet')
events = spark.read.parquet('out/events.parquet')
```

Схему лучше задавать явно: `inferSchema=True` читает файл лишний раз и может угадать тип неверно.

**Parquet** — колоночный формат с типами, сжатием и статистикой min/max по блокам ([почему колонки быстрее](../../../backend/databases/storage/README.md#строки-и-колонки)). Это стандарт для хранения данных под Spark: запрос читает только нужные колонки и пропускает блоки, которые не проходят фильтр.

Замер из прогона `task_stats.py` (условия — в разделе [Когда Spark не нужен](#когда-spark-не-нужен)):

```text
партиций при чтении CSV: 2
count() по CSV: 13.7 с
запись Parquet: 20.6 с
агрегат по CSV    : 8.8 с
агрегат по Parquet: 3.4 с
```

Один и тот же `groupBy` по Parquet в 2,6 раза быстрее, чем по CSV: читаются две колонки из шести, и их не нужно разбирать из текста. 165 МБ CSV делятся на 2 партиции, потому что Spark режет файлы на куски по `spark.sql.files.maxPartitionBytes` (128 МБ).

#### groupBy, join и Spark SQL

```python
by_project = (
    events.join(tasks, 'task_id')
    .groupBy('project', F.date_trunc('month', 'ts').alias('month'))
    .agg(F.count('*').alias('events'), F.countDistinct('user_id').alias('users'))
    .orderBy('month', 'project')
)
by_project.filter(F.col('month') == '2026-03-01').show()
```

```text
+--------+-------------------+------+-----+
| project|              month|events|users|
+--------+-------------------+------+-----+
| backend|2026-03-01 00:00:00| 61958| 5000|
|  design|2026-03-01 00:00:00| 61845| 5000|
|frontend|2026-03-01 00:00:00| 62201| 5000|
|   infra|2026-03-01 00:00:00| 62158| 5000|
|  mobile|2026-03-01 00:00:00| 61836| 5000|
+--------+-------------------+------+-----+
```

`by_project.explain()` показывает физический план (сокращён, читать снизу вверх):

```text
AdaptiveSparkPlan isFinalPlan=false
+- Sort [month ASC, project ASC]
   +- Exchange rangepartitioning(month, project, 200)                         ← shuffle для сортировки
      +- HashAggregate(keys=[project, month], functions=[count(1), count(distinct user_id)])
         +- Exchange hashpartitioning(project, month, 200)                    ← shuffle для groupBy
            +- HashAggregate(...partial_count(distinct user_id))
               +- HashAggregate(keys=[project, month, user_id], ...)
                  +- Exchange hashpartitioning(project, month, user_id, 200)  ← shuffle для countDistinct
                     +- HashAggregate(keys=[project, month, user_id], functions=[partial_count(1)])
                        +- BroadcastHashJoin [task_id], [task_id], Inner, BuildRight
                           :- FileScan parquet [task_id, user_id, ts]          ← только 3 колонки из 6
                           +- BroadcastExchange                                ← справочник задач разослан целиком
                              +- FileScan csv [task_id, project]
```

Что в нём видно:

- **BroadcastHashJoin** — справочник задач (2,5 МБ) меньше порога в 10 МБ, и Spark разослал его экзекьюторам вместо перемешивания трёх миллионов событий;
- **FileScan parquet** читает только `task_id`, `user_id`, `ts` — остальные колонки оптимизатор выбросил сам;
- **три `Exchange`** — три shuffle: `countDistinct` требует сначала сгруппировать по `(project, month, user_id)`, затем по `(project, month)`, а `orderBy` — ещё один обмен. По 200 партиций каждый (`spark.sql.shuffle.partitions`), AQE во время выполнения объединяет мелкие партиции;
- **`HashAggregate` дважды подряд** — частичная агрегация до shuffle (partial) и финальная после: по сети едут уже свёрнутые счётчики, а не все строки.

Тот же DataFrame можно зарегистрировать как таблицу и писать на SQL — план и скорость будут те же:

```python
events.createOrReplaceTempView('events')
tasks.createOrReplaceTempView('tasks')
spark.sql("""
    SELECT e.user_id,
           count(*)                                        AS events,
           count_if(e.event_type = 'closed')               AS closed,
           count_if(e.event_type = 'closed' AND t.priority = 1) AS closed_urgent
    FROM events e JOIN tasks t USING (task_id)
    GROUP BY e.user_id
    ORDER BY closed DESC, events DESC
    LIMIT 5
""").show()
```

```text
+-------+------+------+-------------+
|user_id|events|closed|closed_urgent|
+-------+------+------+-------------+
|    377|   581|    51|            8|
|    915|   649|    49|           13|
|   1589|   646|    49|           12|
|   3286|   612|    48|           12|
|   4643|   604|    48|           13|
+-------+------+------+-------------+
```

#### Запись результата

```python
by_project.write.mode('overwrite').partitionBy('project').parquet('out/stats_by_project.parquet')
```

`partitionBy` раскладывает файлы по папкам `project=backend/`, `project=mobile/`… Запрос с фильтром по проекту прочитает только свою папку. Результат — каталог из нескольких файлов, по одному на задачу: Spark пишет параллельно.

## Частые ошибки

- **`collect()` или `toPandas()` на больших данных.** Всё едет в драйвер → `OutOfMemoryError` → агрегировать в Spark и собирать только итог, или писать результат в файл.
- **Python UDF вместо встроенных функций.** Каждая строка уходит из JVM в Python и обратно, оптимизатор слеп → функции из `pyspark.sql.functions`, в крайнем случае pandas UDF (векторные).
- **Повторные действия без кэша.** Три `count()` по одному DataFrame — три чтения исходников → `cache()` для переиспользуемых промежуточных результатов.
- **Тысячи мелких файлов.** Запись после shuffle с 200 партициями даёт 200 файлов по килобайту → `coalesce(n)` перед записью или AQE.
- **CSV как рабочий формат.** Медленно, без типов, читается целиком → один раз переложить в Parquet.
- **Перекос ключа в join.** Одна задача работает в сто раз дольше остальных → AQE skew join, «соль» (salting) для горячего ключа.

## Когда Spark не нужен

Spark окупается, когда данных действительно много: сотни гигабайт и больше, или когда обработку нужно распределить по кластеру, который у вас уже есть. Ниже этого порога накладные расходы — JVM, планирование, shuffle через диск — съедают выигрыш.

Те же операции на тех же 3 миллионах строк ([examples/duckdb_stats.py](examples/duckdb_stats.py)) в том же контейнере и с тем же числом потоков (2):

| Операция | Spark 4.1.3, `local[2]` | DuckDB 1.5.6, 2 потока |
|---|---|---|
| `count()` с фильтром по CSV | 13,7 с | 3,9 с |
| CSV → Parquet | 20,6 с | 6,6 с |
| агрегат по CSV | 8,8 с | 4,1 с |
| агрегат по Parquet | 3,4 с | 0,18 с |
| join + group by по Parquet | — | 1,3 с |
| весь прогон, включая запуск | 5 мин 25 с | — |

Условия: Apple M1, Docker Desktop с виртуальной машиной на 4 ГБ, в которой параллельно работали чужие контейнеры (Kafka, ClickHouse, Elasticsearch); Spark запускался с `--driver-memory 512m` — с 1 ГБ его дважды убил OOM-killer виртуальной машины. Абсолютные цифры поэтому завышены и шумные, но порядок разницы показателен: на данных, которые помещаются на одну машину, DuckDB быстрее в 2–20 раз и запускается мгновенно. На хосте без виртуализации DuckDB с 8 потоками сделал агрегат по Parquet за 0,01 с, а join — за 0,46 с.

- **pandas / Polars** — данные помещаются в память (единицы гигабайт);
- **DuckDB** — SQL по Parquet и CSV на одной машине, десятки и сотни гигабайт, без сервера;
- **[ClickHouse](../../../backend/databases/clickhouse/README.md)** — данные постоянно пополняются и к ним много интерактивных запросов;
- **[PostgreSQL](../../../backend/databases/postgres/README.md)** — данные транзакционные, а отчёт — несколько миллионов строк.

Spark остаётся хорошим выбором для тяжёлых ETL по озеру данных (data lake), обучения моделей на больших выборках (MLlib) и потоковой обработки (Structured Streaming). Оркестрируют такие задания обычно через [Airflow](../airflow/README.md).

## Связанные темы

- [Как базы данных хранят данные](../../../backend/databases/storage/README.md) — колонки, LSM, сжатие
- [ClickHouse](../../../backend/databases/clickhouse/README.md) — альтернатива для аналитики по событиям
- [Airflow](../airflow/README.md) — запуск Spark-заданий по расписанию
- [S3](../../../backend/databases/s3/README.md) — объектное хранилище, где обычно лежат Parquet-файлы
