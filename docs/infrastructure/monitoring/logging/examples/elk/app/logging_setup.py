import logging
import logging.config

from flask import g, has_request_context


class RequestIdFilter(logging.Filter):
    """Добавляет request_id текущего запроса в каждую запись лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = g.get('request_id') if has_request_context() else None
        return True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {'request_id': {'()': RequestIdFilter}},
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.json.JsonFormatter',
            'fmt': '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s',
            'rename_fields': {'asctime': 'timestamp', 'levelname': 'level', 'name': 'logger'},
            'json_ensure_ascii': False,
        },
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'json',
            'filters': ['request_id'],
        },
    },
    'root': {'level': 'INFO', 'handlers': ['stdout']},
    'loggers': {
        # gunicorn по умолчанию пишет в свои обработчики — переводим их на общий JSON
        'gunicorn.error': {'handlers': ['stdout'], 'propagate': False, 'level': 'INFO'},
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING)
