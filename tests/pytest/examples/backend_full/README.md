## Запуск сервиса

Подготовьте переменные окружения из файла `.env.example`.

Для создания ключей можно воспользоваться следующим способом:
```shell
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Запустите сервис локально:
```shell
docker-compose -p example-test up -d --build
```

Если выходит ошибка `exec /app/entrypoint.sh: permission denied`, то нужно вручную установить флаг выполнения для entrypoint.sh в локальной системе:
```shell
chmod +x app/entrypoint.sh
```

Создание миграциий:
```shell
docker exec -it example-test-app alembic revision --autogenerate -m "init migration"
```

Применение миграции (при перезапуске сервиса делается автоматически):
```shell
docker exec -it example-test-app alembic upgrade head
```

Создание демонстрационных данных
```shell
docker exec -it example-test-app python -m scripts.create_demo_data
```

Удаление сервиса с БД:
```shell
docker-compose -p example-test down -v
```

## Выполнение функциональных тестов

Запуск тестов в контейнерах
```sh
docker-compose -f tests/functional/docker-compose.yml -p example-functional-test up --build --abort-on-container-exit
```

Удаление тестов:
```sh
docker-compose -f tests/functional/docker-compose.yml -p example-functional-test down -v
```