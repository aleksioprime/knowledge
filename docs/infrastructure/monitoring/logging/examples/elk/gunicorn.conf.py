from app.logging_setup import LOGGING

bind = '0.0.0.0:8000'
workers = 2
accesslog = None  # журнал запросов пишет nginx
logconfig_dict = LOGGING
