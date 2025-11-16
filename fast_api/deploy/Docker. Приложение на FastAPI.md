Создание файла, содержащего все зависимости нашего проекта:

```sh
pip freeze > requirements.txt
```

Создание Dockerfile (текстовый файл, который содержит инструкции о том, как будет создан docker-образ):

```dockerfile
# pull the official base image
FROM python:3.12.0-alpine

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# set work directory
WORKDIR /usr/src/app

# copy project to work directory
COPY . .

# update pip and install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
```

Cодержимое файла:

- `FROM python:3.12.0-alpine`: Устанавливает базовый образ, на основе которого будет создан контейнер Docker.
- `ENV PYTHONDONTWRITEBYTECODE=1`: Не позволяет Python создавать файлы `.pyc` в контейнере.
- `ENV PYTHONUNBUFFERED=1`: Гарантирует, что вывод Python регистрируется в терминале, что позволяет отслеживать логи FastAPI в режиме реального времени.
- `WORKDIR /usr/src/app`: Устанавливает рабочий каталог внутри контейнера в `/usr/src/app`.
- `COPY . .`: Копирует весь исходный код проекта в рабочий каталог в контейнере.
- `RUN pip install --upgrade pip && pip install -r requirements.txt`: Устанавливает и обновляет версию pip, которая находится в контейнере, а затем устанавливает все необходимые модули проекта для запуска в контейнере.
- `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]`: Устанавливает исполняемые команды в контейнере.

Создание `.dockerignore`:

```
.venv
__pycache__
.idea
*/Dockerfile*
.dockerignore
```

Создание образа Docker из файла Dockerfile:

```sh
docker build --tag fastapi_hello_word:latest .
```

- `--tag` Устанавливает тег для образа. Например, мы создаем образ Docker из `python:3.12.0` у него есть тег `alpine`.  
    В нашем образе Docker, `latest` это тег.
- Точка `.` указывает на то, что `Dockerfile` находится в текущем рабочем каталоге.

Создание и запуск контейнера Docker из образа:

```sh
docker run --name fastapi_hello_word -d -p 80:80 fastapi_hello_word:latest
```

- `--name`: Устанавливает имя контейнера Docker.
- `-d`: Заставляет образ работать  в фоновом режиме.
- `-p 80:80`: Сопоставляет порт `80` в контейнере Docker с портом `80` на локальном хосте.
- `fastapi_hello_word:latest`: Указывает, какой образ используется для сборки контейнера Docker.

