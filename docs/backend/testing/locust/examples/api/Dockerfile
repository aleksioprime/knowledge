FROM python:3.12-slim

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Запускаем uvicorn на порту 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]