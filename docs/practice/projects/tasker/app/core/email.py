import logging

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    # Учебная заглушка: вместо SMTP пишем письмо в лог
    logger.info('Письмо для %s: %s — %s', to, subject, body)
