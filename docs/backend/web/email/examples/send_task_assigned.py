"""Письмо «вам назначена задача»: шаблон, MIME, отправка и проверка через API Mailpit."""

from datetime import datetime, timezone

from jinja2 import UndefinedError

from mailer import BOUNCE_ADDRESS, SITE_URL, build_message, clear_mailbox, connect, mailpit, render

anna = {'name': 'Анна', 'email': 'anna@example.com', 'timezone': 'Asia/Yekaterinburg'}
boris = {'name': 'Борис'}
task = {
    'id': 42,
    'title': 'Отчёт <script>alert(1)</script> & итоги',
    'due_at': datetime(2026, 10, 31, 13, 0, tzinfo=timezone.utc),
    'labels': ['отчёт', 'срочно'],
}
context = {
    'user': anna,
    'author': boris,
    'task': task,
    'task_url': f'{SITE_URL}/tasks/42?utm_source=email&utm_campaign=task_assigned',
    'unsubscribe_url': f'{SITE_URL}/unsubscribe/u1-token',
}

clear_mailbox()

subject, text, html = render('task_assigned', **context)
message = build_message(anna['email'], subject, text, html, unsubscribe_token='u1-token')

print('Структура письма:')
for part in message.walk():
    print(' ', part.get_content_type())

raw = message.as_string()
print('\nТема в сыром письме:', next(line for line in raw.splitlines() if line.startswith('Subject:')))

with connect() as smtp:
    smtp.send_message(message, from_addr=BOUNCE_ADDRESS)

summary = mailpit('/messages')['messages'][0]
detail = mailpit(f"/message/{summary['ID']}")
headers = mailpit(f"/message/{summary['ID']}/headers")

print('\nЧто пришло в Mailpit:')
print('  Subject:', detail['Subject'])
print('  From:', detail['From']['Name'], detail['From']['Address'], '| Return-Path:', headers['Return-Path'][0])
print('  текстовая часть:', bool(detail['Text']), '| HTML-часть:', bool(detail['HTML']))
print('  List-Unsubscribe:', headers['List-Unsubscribe'][0])
print('  List-Unsubscribe-Post:', headers['List-Unsubscribe-Post'][0])
print('  Message-ID:', headers['Message-Id'][0])
print('\nТекстовая версия:\n' + detail['Text'])
html_line = next(line for line in detail['HTML'].splitlines() if 'назначил' in line)
print('Строка из HTML:', html_line.strip())

assert detail['Subject'] == subject
assert detail['Text'] and detail['HTML']
assert '&lt;script&gt;' in detail['HTML'] and '<script>' not in detail['HTML']
assert headers['List-Unsubscribe-Post'] == ['List-Unsubscribe=One-Click']

print('\nЗабыли передать пользователя:')
broken = {key: value for key, value in context.items() if key != 'user'}
try:
    render('task_assigned', **broken)
except UndefinedError as error:
    print('  UndefinedError:', error)
