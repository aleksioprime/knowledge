"""Каждый день забирает задачи из учебного API и сохраняет статистику по пользователям в PostgreSQL."""
from datetime import datetime, timedelta

import httpx
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task

API_URL = 'https://jsonplaceholder.typicode.com/todos'


@dag(
    schedule='@daily',
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args={'retries': 3, 'retry_delay': timedelta(minutes=5)},
    tags=['учебный'],
)
def todo_stats():
    @task
    def extract() -> list[dict]:
        response = httpx.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()

    @task
    def transform(todos: list[dict]) -> list[dict]:
        stats: dict[int, dict] = {}
        for todo in todos:
            user = stats.setdefault(todo['userId'], {'user_id': todo['userId'], 'total': 0, 'done': 0})
            user['total'] += 1
            user['done'] += todo['completed']
        return list(stats.values())

    @task
    def load(stats: list[dict], ds: str | None = None) -> int:
        hook = PostgresHook(postgres_conn_id='warehouse')
        hook.run('''
            CREATE TABLE IF NOT EXISTS todo_stats (
                day DATE, user_id INT, total INT, done INT,
                PRIMARY KEY (day, user_id)
            )
        ''')
        # Повторный запуск за тот же день перезапишет строки, а не задублирует их
        for row in stats:
            hook.run(
                '''
                INSERT INTO todo_stats (day, user_id, total, done) VALUES (%s, %s, %s, %s)
                ON CONFLICT (day, user_id) DO UPDATE SET total = EXCLUDED.total, done = EXCLUDED.done
                ''',
                parameters=(ds, row['user_id'], row['total'], row['done']),
            )
        return len(stats)

    load(transform(extract()))


todo_stats()
