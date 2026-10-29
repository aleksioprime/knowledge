# База знаний

Конспекты и примеры кода. Материалы представлены в виде обычных файлов (`.py`, `.md`) и Jupyter Notebook (`.ipynb`).

## Разделы

- [Математика](math/README.md) — теория чисел, степени и логарифмы, e и экспонента, производные, интегралы
- [Python](python/README.md) — основы языка, ООП, функции, типизация, импорты, стандартная библиотека, алгоритмы, многозадачность, livecoding
- [Фреймворки](framework/README.md) — FastAPI, Django, Celery, Dramatiq
- [Базы данных и хранилища](data/README.md) — PostgreSQL, SQLAlchemy, MongoDB, Redis, ClickHouse, Elasticsearch, S3, Airflow
- [Микросервисы](microservices/README.md) — брокеры сообщений, HTTPX, API Gateway, Keycloak
- [Веб-протоколы и инфраструктура](web/README.md) — HTTP, веб-безопасность, передача файлов и NGINX
- [Тестирование](tests/README.md) — Pytest, Locust, Postman
- [CI/CD](ci_cd/README.md) — GitHub Actions, Kubernetes, Portainer
- [DevTools](devtools/README.md) — Docker, Git, линтеры, Poetry, uv, pyenv
- [Linux](linux/README.md) — администрирование и настройка сервера
- [Computer Vision](cv/README.md) — NumPy, OpenCV
- [Machine Learning](ml/README.md) — pandas, первая модель, метрики, переобучение, модель в FastAPI
- [Мониторинг и аналитика](analyze/README.md) — Prometheus, Grafana
- [Системный дизайн](design/README.md) — принципы и паттерны проектирования
- [JavaScript](javascript/README.md) — основы языка, коллекции, асинхронность, модули и браузерные API
- [Frontend (Vue.js)](vuejs/README.md) — заметки по фронтенду
- [Pet-проекты](pet/README.md) — учебные сервисы и эксперименты

## Как устроены заметки

Новые заметки пишутся по [шаблону](_template.md): задача → минимальный пример → как работает → частые ошибки → когда не использовать. Там же правила стиля для текста и кода.

Сквозной учебный проект — [«Задачник»](pet/tasker/README.md): на нём показаны FastAPI, базы данных, кэш, фоновые задачи и мониторинг.

## Сайт

Заметки собираются в сайт на VitePress: поиск, тёмная тема, анимации процессов и запуск Python прямо на странице. Пример — [цикл событий asyncio наглядно](python/multitask/event_loop_visual.md).

```bash
npm install
npm run dev
```

Чтобы фрагмент Python можно было запустить в браузере, пометьте блок кода как `python run`. Код выполняется через Pyodide, поэтому сторонние сервисы (базы, брокеры, сеть) в таких примерах недоступны.

