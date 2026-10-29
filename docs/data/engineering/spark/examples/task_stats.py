"""Статистика по журналу событий задач на PySpark.

spark-submit --master 'local[2]' task_stats.py /data [/out]
"""

import sys
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, LongType, StringType, StructField, StructType, TimestampType

data = sys.argv[1] if len(sys.argv) > 1 else 'data'
out = sys.argv[2] if len(sys.argv) > 2 else data

spark = SparkSession.builder.appName('task-stats').getOrCreate()
spark.sparkContext.setLogLevel('WARN')
print('Spark', spark.version, '| master', spark.sparkContext.master)


def timed(title, action):
    started = time.perf_counter()
    result = action()
    print(f'{title}: {time.perf_counter() - started:.1f} с')
    return result


events_schema = StructType([
    StructField('event_id', LongType()),
    StructField('task_id', IntegerType()),
    StructField('user_id', IntegerType()),
    StructField('event_type', StringType()),
    StructField('ts', TimestampType()),
    StructField('duration_ms', IntegerType()),
])

# --- ленивость: чтение и фильтр ничего не выполняют ---------------------------
started = time.perf_counter()
events_csv = spark.read.csv(f'{data}/events.csv', header=True, schema=events_schema)
closed = events_csv.filter(F.col('event_type') == 'closed').select('task_id', 'ts')
print(f'план построен за {time.perf_counter() - started:.2f} с, данных ещё не читали')
print('событий closed:', timed('count() по CSV', closed.count))

# --- CSV → Parquet -------------------------------------------------------------
print('партиций при чтении CSV:', events_csv.rdd.getNumPartitions())
timed('запись Parquet', lambda: events_csv.write.mode('overwrite').parquet(f'{out}/events.parquet'))
events = spark.read.parquet(f'{out}/events.parquet')
tasks = spark.read.csv(f'{data}/tasks.csv', header=True, inferSchema=True)

timed('агрегат по CSV    ', lambda: events_csv.groupBy('event_type').agg(F.avg('duration_ms')).collect())
timed('агрегат по Parquet', lambda: events.groupBy('event_type').agg(F.avg('duration_ms')).collect())

# --- groupBy / agg ------------------------------------------------------------
by_type = (
    events.groupBy('event_type')
    .agg(F.count('*').alias('events'), F.round(F.avg('duration_ms')).alias('avg_ms'))
    .orderBy(F.desc('events'))
)
by_type.show()

# --- join: события × справочник задач -----------------------------------------
by_project = (
    events.join(tasks, 'task_id')
    .groupBy('project', F.date_trunc('month', 'ts').alias('month'))
    .agg(F.count('*').alias('events'), F.countDistinct('user_id').alias('users'))
    .orderBy('month', 'project')
)
by_project.filter(F.col('month') == '2026-03-01').show()
by_project.explain()

# --- Spark SQL: то же самое через SQL -------------------------------------------
events.createOrReplaceTempView('events')
tasks.createOrReplaceTempView('tasks')
top_users = spark.sql("""
    SELECT e.user_id,
           count(*)                                        AS events,
           count_if(e.event_type = 'closed')               AS closed,
           count_if(e.event_type = 'closed' AND t.priority = 1) AS closed_urgent
    FROM events e JOIN tasks t USING (task_id)
    GROUP BY e.user_id
    ORDER BY closed DESC, events DESC
    LIMIT 5
""")
top_users.show()

# --- запись результата ----------------------------------------------------------
by_project.write.mode('overwrite').partitionBy('project').parquet(f'{out}/stats_by_project.parquet')
print('shuffle-партиций по умолчанию:', spark.conf.get('spark.sql.shuffle.partitions'))

spark.stop()
