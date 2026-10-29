import logging
import uuid

from flask import Flask, abort, g, jsonify, request

from app.logging_setup import setup_logging

setup_logging()
logger = logging.getLogger('tasker')

app = Flask(__name__)
app.json.ensure_ascii = False
TASKS = {1: {'id': 1, 'title': 'Сдать отчёт'}, 2: {'id': 2, 'title': 'Позвонить клиенту'}}


@app.before_request
def bind_request_id():
    # nginx передаёт свой $request_id; если запрос пришёл в обход nginx — генерируем сами
    g.request_id = request.headers.get('X-Request-Id') or uuid.uuid4().hex


@app.after_request
def return_request_id(response):
    response.headers['X-Request-Id'] = g.request_id
    return response


@app.get('/tasks')
def list_tasks():
    logger.info('Список задач', extra={'count': len(TASKS)})
    return jsonify(list(TASKS.values()))


@app.get('/tasks/<int:task_id>')
def get_task(task_id: int):
    if task_id == 13:
        try:
            raise ConnectionError('база не отвечает')
        except ConnectionError:
            logger.exception('Не удалось прочитать задачу', extra={'task_id': task_id})
            abort(503)
    if task_id not in TASKS:
        logger.warning('Задача не найдена', extra={'task_id': task_id})
        abort(404)
    return jsonify(TASKS[task_id])
