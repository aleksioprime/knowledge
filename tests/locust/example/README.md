# Locust Load Testing Example

Минималистичный пример приложения для нагрузочного тестирования с использованием Locust, FastAPI и PostgreSQL.

## Структура проекта

```
example/
├── app/                    # FastAPI приложение
│   ├── src/               # Исходный код приложения
│   │   ├── api.py        # API маршруты
│   │   ├── config.py     # Конфигурация
│   │   ├── crud.py       # CRUD операции
│   │   ├── db.py         # Подключение к БД
│   │   ├── dependencies.py  # Зависимости FastAPI
│   │   ├── init_db.py    # Инициализация тестовых данных
│   │   ├── main.py       # Главный файл приложения
│   │   ├── models.py     # Модели SQLAlchemy
│   │   ├── schemas.py    # Pydantic схемы
│   │   └── security.py   # JWT аутентификация
│   ├── Dockerfile
│   └── requirements.txt
├── locust/                # Locust тесты
│   ├── locustfile.py     # Сценарии нагрузочного тестирования
│   ├── Dockerfile
│   └── requirements.txt
└── docker-compose.yaml    # Конфигурация Docker Compose
```

## Запуск

```bash
# Запуск всех сервисов
docker-compose up --build

# Остановка сервисов
docker-compose down

# Полная очистка (включая volumes)
docker-compose down -v
```

## Доступ к сервисам

- **API**: http://localhost:7002
- **API документация**: http://localhost:7002/docs
- **Locust веб-интерфейс**: http://localhost:8089
- **Adminer (управление БД)**: http://localhost:7001

## Тестовые данные

При запуске автоматически создается тестовый пользователь:
- Username: `user1`
- Password: `password`

## API эндпоинты

- `POST /api/auth/login` - Авторизация
- `GET /api/profile` - Получить профиль пользователя
- `GET /api/items` - Получить список элементов
- `POST /api/items` - Создать новый элемент

## Использование Locust

1. Откройте http://localhost:8089
2. Укажите количество пользователей и скорость их появления
3. Запустите тест
4. Наблюдайте за результатами в реальном времени
