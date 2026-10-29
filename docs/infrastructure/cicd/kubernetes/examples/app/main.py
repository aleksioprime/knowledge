import os
import socket

from fastapi import FastAPI

app = FastAPI()


@app.get('/')
def index() -> dict:
    return {
        'pod': socket.gethostname(),
        'version': os.environ.get('APP_VERSION', 'dev'),
        'greeting': os.environ.get('GREETING', 'Привет'),
        'has_secret': bool(os.environ.get('API_KEY')),
    }


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}
