FROM python:3.12-slim

WORKDIR /locust

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы конфигурации Locust
COPY . .

# По умолчанию запускаем Locust в режиме standalone
CMD ["locust", "-f", "locustfile.py", "--host", "http://api:8000", "--web-host", "0.0.0.0"]