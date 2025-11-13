# Locust Load Testing Example

Минималистичный пример приложения для нагрузочного тестирования с использованием Locust, FastAPI и PostgreSQL.

## Запуск проекта

```bash
# Запуск всех сервисов
docker-compose -p test-locust up --build -d

# Остановка сервисов
docker-compose -p test-locust down

# Полная очистка (включая volumes)
docker-compose -p test-locust down -v
```

## Доступ к сервисам

- **API**: http://localhost:7002
- **API документация**: http://localhost:7002/docs
- **Locust веб-интерфейс**: http://localhost:8089
- **Adminer (управление БД)**: http://localhost:7001

## Тестовые данные

При запуске автоматически создается тестовый пользователь:
- Username: `user_test`
- Password: `password`

## API эндпоинты

- `POST /api/auth/login` - Авторизация
- `GET /api/profile` - Получить профиль пользователя
- `GET /api/items` - Получить список элементов
- `POST /api/items` - Создать новый элемент

## Использование Locust

1. Откройте http://localhost:7003
2. Укажите количество пользователей и скорость их появления
3. Запустите тест
4. Наблюдайте за результатами в реальном времени
