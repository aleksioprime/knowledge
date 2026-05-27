# Apache Airflow

**Apache Airflow** — платформа для программного создания, планирования и мониторинга пайплайнов данных (ETL/ELT). Пайплайны описываются на Python в виде DAG (Directed Acyclic Graph).

Основные сущности:
- **DAG** — ориентированный ациклический граф из задач
- **Task / Operator** — единичная операция (PythonOperator, BashOperator, KubernetesPodOperator и т.д.)
- **Scheduler** — планирует и запускает DAG-и
- **Executor** — выполняет задачи (Local, Celery, Kubernetes)
- **XCom** — обмен данными между задачами
- **Hooks/Connections** — интеграция с внешними системами

## Содержание

> Заметки и примеры будут добавляться по мере проработки темы.
