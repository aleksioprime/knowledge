# Задачи на Django

Тот же API задач, что в [«Задачнике»](../../../../practice/projects/tasker/README.md) на FastAPI, но на Django и Django REST Framework, с админкой. Разбор кода — в заметках раздела [Django](../README.md).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- админка: http://localhost:8000/admin/
- API: http://localhost:8000/api/tasks/ — в браузере откроется страница DRF, где можно войти и отправлять запросы;
- тесты: `python manage.py test` (6 тестов).

```bash
curl -u admin:ваш-пароль localhost:8000/api/tasks/
curl -u admin:ваш-пароль -X POST localhost:8000/api/tasks/ -H 'Content-Type: application/json' -d '{"title": "Сдать отчёт"}'
```

Данные хранятся в SQLite (`db.sqlite3`), чтобы пример запускался без сервера базы данных.
