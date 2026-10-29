# Django

**Django** — Python-фреймворк по принципу «всё включено»: ORM, миграции, админка, пользователи и права, формы, шаблоны и middleware есть из коробки. Для API к нему добавляют Django REST Framework (DRF).

Заметки идут по порядку. Все примеры взяты из учебного проекта [example](example/README.md) — API задач с админкой, тот же по смыслу, что [«Задачник» на FastAPI](../../pet/tasker/README.md).

## Содержание

1. [Структура проекта](docs/project.md) — проект и приложения, путь запроса, настройки и их разбиение на файлы, команды `manage.py`, переводы
2. [ORM](docs/orm.md) — модели, ленивые QuerySet, фильтры, связи, агрегация, `F()`, N+1 и `select_related` / `prefetch_related`, как увидеть SQL-запросы
3. [Миграции](docs/migrations.md) — устройство файла миграции, `django_migrations`, `sqlmigrate`, откат, `--fake`, `RunPython` и `RunSQL`, конфликты веток, опасные операции
4. [Транзакции, массовые операции и сырой SQL](docs/transactions.md) — `atomic` и savepoint, `select_for_update`, `on_commit`, `bulk_create` / `bulk_update`, `raw()`, `cursor()`, свой `Func`
5. [Сигналы](docs/signals.md) — `post_save`, `m2m_changed`, `post_migrate`, регистрация в `AppConfig.ready()`, минусы и когда лучше явный вызов
6. [Админка](docs/admin.md) — регистрация моделей, список, фильтры, поиск, массовые действия
7. [Django REST Framework](docs/drf.md) — сериализаторы, `ModelViewSet`, роутер, права, тесты, сравнение с FastAPI
8. [Пользователи и внешняя аутентификация](docs/auth.md) — своя модель пользователя, `get_user_model()`, бэкенды аутентификации, вход в админку через Auth-сервис, SSO, сессии и CSRF
