FROM python:3.12-slim

ARG VERSION=dev
ENV APP_VERSION=$VERSION

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
