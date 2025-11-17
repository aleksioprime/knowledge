## Запуск сервиса

Подготовьте переменные окружения из файла `.env.example`.

Для создания ключей можно воспользоваться следующим способом:
```shell
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Запустите сервис локально:
```shell
docker-compose -p example-fastapi up -d --build
```

Если выходит ошибка `exec /app/entrypoint.sh: permission denied`, то нужно вручную установить флаг выполнения для entrypoint.sh в локальной системе:
```shell
chmod +x app/entrypoint.sh
```