# gRPC-сервис задач

Пример к заметке [«Проектирование API: REST, версионирование, gRPC»](../../api_design.md): контракт `TaskService` в `tasks.proto`, сервер на `grpcio` и клиент, который вызывает все три метода.

Файлы:

- `tasks.proto` — контракт: сервис и сообщения;
- `server.py` — сервер, хранит задачи в памяти;
- `client.py` — создаёт задачу, читает её, получает список и показывает ошибки.

## Запуск

Нужен Python 3.12.

```bash
cd docs/backend/web/http/examples/grpc
python -m venv .venv && source .venv/bin/activate
pip install grpcio grpcio-tools

# Генерация кода из контракта: tasks_pb2.py, tasks_pb2.pyi, tasks_pb2_grpc.py
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. tasks.proto

python server.py
# gRPC-сервер слушает порт 50051
```

В другом терминале:

```bash
python client.py
```

```text
Создана: 3 Позвонить врачу ['здоровье']
Получена: 3 Позвонить врачу открыта
Открытые: ['Сдать отчёт', 'Позвонить врачу']
Размер сообщения: 51 байт
Ошибка: NOT_FOUND - Задача 999 не найдена
Ошибка: INVALID_ARGUMENT - Название не может быть пустым
```

Сгенерированные `*_pb2*.py` не хранятся в репозитории (см. `.gitignore`): они получаются из `tasks.proto` командой выше. После любого изменения контракта генерацию нужно повторить.

## Вызов без клиента на Python

[grpcurl](https://github.com/fullstorydev/grpcurl) — аналог `curl` для gRPC. Сервер в примере не включает рефлексию, поэтому контракт передаётся флагом `-proto`:

```bash
grpcurl -plaintext -proto tasks.proto -d '{"id": 1}' localhost:50051 tasker.v1.TaskService/GetTask
```
