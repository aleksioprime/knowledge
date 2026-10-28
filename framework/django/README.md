# Django

**Django** — Python-фреймворк по принципу «всё включено»: ORM, миграции, админка, пользователи и права, формы, шаблоны и middleware есть из коробки. Для API к нему добавляют Django REST Framework (DRF).

Заметки идут по порядку. Все примеры взяты из учебного проекта [example](example/README.md) — API задач с админкой, тот же по смыслу, что [«Задачник» на FastAPI](../../pet/tasker/README.md).

## Содержание

1. [Структура проекта](docs/project.md) — проект и приложения, путь запроса, настройки, команды `manage.py`, миграции
2. [ORM](docs/orm.md) — модели, ленивые QuerySet, фильтры, связи, агрегация, `F()`, N+1 и `select_related` / `prefetch_related`
3. [Админка](docs/admin.md) — регистрация моделей, список, фильтры, поиск, массовые действия
4. [Django REST Framework](docs/drf.md) — сериализаторы, `ModelViewSet`, роутер, права, тесты, сравнение с FastAPI
