FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gunicorn.conf.py .
COPY app ./app
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
