"""Общие части примера: настройки стенда, шаблоны, сборка письма, API Mailpit."""

import json
import os
import smtplib
import ssl
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

SMTP_HOST = os.getenv('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.getenv('SMTP_PORT', '41025'))
SMTP_USER = os.getenv('SMTP_USER', 'tasker')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'test-app-password')  # Mailpit примет любой
MAILPIT_API = os.getenv('MAILPIT_API', 'http://localhost:48025/api/v1')

SENDER = formataddr(('Задачник', 'notify@tasker.test'))
BOUNCE_ADDRESS = 'bounces@tasker.test'
SITE_URL = 'https://tasker.test'

MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
          'августа', 'сентября', 'октября', 'ноября', 'декабря']


def localtime(value: datetime, tz: str) -> str:
    """Дата в часовом поясе получателя: 31 октября, 18:00."""
    local = value.astimezone(ZoneInfo(tz))
    return f'{local.day} {MONTHS[local.month - 1]}, {local:%H:%M}'


env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / 'templates'),
    autoescape=select_autoescape(['html']),   # .html экранируется, .txt — нет
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters['localtime'] = localtime


def render(name: str, **context) -> tuple[str, str, str]:
    """Возвращает тему, текстовую и HTML-версию письма."""
    subject = env.get_template(f'{name}.subject.txt').render(context).strip()
    text = env.get_template(f'{name}.txt').render(context)
    html = env.get_template(f'{name}.html').render(context, subject=subject)
    return subject, text, html


def build_message(to: str, subject: str, text: str, html: str, unsubscribe_token: str) -> EmailMessage:
    message = EmailMessage()
    message['From'] = SENDER
    message['To'] = to
    message['Subject'] = subject
    message['Message-ID'] = make_msgid(domain='tasker.test')
    message['List-Unsubscribe'] = (
        f'<{SITE_URL}/unsubscribe/{unsubscribe_token}>, '
        f'<mailto:unsubscribe@tasker.test?subject={unsubscribe_token}>'
    )
    message['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
    message.set_content(text)
    message.add_alternative(html, subtype='html')
    return message


def tls_context() -> ssl.SSLContext:
    # у Mailpit самоподписанный сертификат; с настоящим сервером — ssl.create_default_context()
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def connect() -> smtplib.SMTP:
    smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
    smtp.starttls(context=tls_context())
    smtp.login(SMTP_USER, SMTP_PASSWORD)
    return smtp


def mailpit(path: str, method: str = 'GET'):
    request = urllib.request.Request(MAILPIT_API + path, method=method)
    with urllib.request.urlopen(request) as response:
        body = response.read()
    return json.loads(body) if body.startswith((b'{', b'[')) else body.decode()


def clear_mailbox() -> None:
    mailpit('/messages', method='DELETE')
