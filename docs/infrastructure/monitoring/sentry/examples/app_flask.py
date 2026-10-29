import sentry_sdk
from flask import Flask, abort, jsonify

sentry_sdk.init(
    dsn='http://public@127.0.0.1:47001/1',
    environment='staging',
    release='tasker@1.4.2',
    traces_sample_rate=1.0,  # для проверки — каждый запрос; в продакшене 0.01–0.1
)

app = Flask(__name__)
TASKS = {1: {'id': 1, 'title': 'Сдать отчёт'}}


@app.get('/tasks/<int:task_id>')
def get_task(task_id: int):
    if task_id not in TASKS:
        abort(404)
    return jsonify(TASKS[task_id])


@app.post('/reports')
def build_report():
    sentry_sdk.add_breadcrumb(category='report', message='Собираем отчёт за октябрь', level='info')
    try:
        1 / 0
    except ZeroDivisionError as error:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag('report', 'monthly')
            scope.fingerprint = ['report-failed']  # все сбои отчёта — одна проблема
            sentry_sdk.capture_exception(error)
    return jsonify(status='queued'), 202
