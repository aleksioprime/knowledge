# База знаний

Конспекты и примеры кода.

## Разделы

### Языки

- [Python](python/README.md) — основы языка, ООП, функции, типизация, импорты, стандартная библиотека, алгоритмы, многозадачность, livecoding
- [JavaScript](javascript/README.md) — основы языка, коллекции, асинхронность, модули и браузерные API
- [Frontend (Vue.js)](vuejs/README.md) — заметки по фронтенду

### Бэкенд

- [Фреймворки](framework/README.md) — FastAPI, Django, Celery, Dramatiq
- [Базы данных и хранилища](data/README.md) — PostgreSQL, SQLAlchemy, MongoDB, Redis, ClickHouse, Elasticsearch, S3, Airflow
- [Микросервисы](microservices/README.md) — брокеры сообщений, HTTPX, API Gateway, Keycloak
- [Веб-протоколы и инфраструктура](web/README.md) — HTTP, веб-безопасность, передача файлов и NGINX
- [Системный дизайн](design/README.md) — принципы и паттерны проектирования
- [Тестирование](tests/README.md) — Pytest, Locust, Postman

### Инфраструктура

- [DevTools](devtools/README.md) — Docker, Git, линтеры, Poetry, uv, pyenv
- [CI/CD](ci_cd/README.md) — GitHub Actions, Kubernetes, Portainer
- [Linux](linux/README.md) — администрирование и настройка сервера
- [Мониторинг и аналитика](analyze/README.md) — Prometheus, Grafana

### Данные и ML

- [Математика](math/README.md) — теория чисел, степени и логарифмы, e и экспонента, производные, интегралы
- [Machine Learning](ml/README.md) — pandas, первая модель, метрики, переобучение, модель в FastAPI
- [Computer Vision](cv/README.md) — NumPy, OpenCV

### Практика

- [Pet-проекты](pet/README.md) — учебные сервисы и эксперименты

## Как устроены заметки

Новые заметки пишутся по [шаблону](_template.md): задача → минимальный пример → как работает → частые ошибки → когда не использовать. Там же правила стиля для текста и кода.

Сквозной учебный проект — [«Задачник»](pet/tasker/README.md): на нём показаны FastAPI, базы данных, кэш, фоновые задачи и мониторинг.

## Сайт

Заметки собираются в сайт на VitePress: поиск, тёмная тема, анимации процессов, запуск Python и SQL прямо на странице. Пример — [цикл событий asyncio наглядно](python/multitask/event_loop_visual.md).

```bash
npm install
npm run dev
```

Чтобы фрагмент можно было запустить в браузере, пометьте блок кода как `python run` или `sql run`:

- Python выполняется через Pyodide, поэтому сторонние сервисы (базы, брокеры, сеть) в таких примерах недоступны;
- SQL выполняется в настоящем PostgreSQL, собранном в WebAssembly (PGlite): у каждого запуска чистая база в памяти и одно соединение;
- `session=имя` связывает блоки одного языка в цепочку: перед запуском молча выполняются блоки выше с тем же именем;
- `setup=имя` помечает подготовку (например, таблицы с данными), а `uses=имя` выполняет перед блоком только её — так примеры не тянут за собой все блоки выше. Их можно сочетать: `session=шаги uses=данные`.
