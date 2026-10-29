"""
Конфигурация логирования для приложения.
Настраивает форматы логов и обработчики для uvicorn и приложения.
"""

# Формат вывода логов: время - имя логгера - уровень - сообщение
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Обработчики логов по умолчанию
LOG_DEFAULT_HANDLERS = ['console']


# Словарь конфигурации логирования в формате Python logging.config
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Форматтеры определяют внешний вид логов
    'formatters': {
        'verbose': {
            'format': LOG_FORMAT,
        },
        'default': {
            '()': 'uvicorn.logging.DefaultFormatter',
            'fmt': '%(levelprefix)s %(message)s',
            'use_colors': None,
        },
        'access': {
            '()': 'uvicorn.logging.AccessFormatter',
            'fmt': "%(levelprefix)s %(client_addr)s - '%(request_line)s' %(status_code)s",
        },
    },

    # Обработчики определяют куда отправляются логи
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'default': {
            'formatter': 'default',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'access': {
            'formatter': 'access',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },

    # Логгеры определяют какие модули логируются и как
    'loggers': {
        '': {
            'handlers': LOG_DEFAULT_HANDLERS,
            'level': 'INFO',
        },
        'uvicorn.error': {
            'level': 'INFO',
        },
        'uvicorn.access': {
            'handlers': ['access'],
            'level': 'INFO',
            'propagate': False,
        },
    },

    # Корневой логгер - используется если не найден специфичный логгер
    'root': {
        'level': 'INFO',
        'formatter': 'verbose',
        'handlers': LOG_DEFAULT_HANDLERS,
    },
}