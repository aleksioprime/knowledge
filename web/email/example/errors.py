"""Временные и постоянные ошибки отправки: что повторять, а что нет."""

import json
import random
import smtplib
import urllib.request
from email.message import EmailMessage

import mailer
from mailer import BOUNCE_ADDRESS, MAILPIT_API, SENDER, clear_mailbox, connect, mailpit


def set_chaos(recipient_code: int, probability: int) -> None:
    """Mailpit умеет отвечать ошибками по заказу (режим chaos)."""
    body = json.dumps({'Recipient': {'ErrorCode': recipient_code, 'Probability': probability}}).encode()
    request = urllib.request.Request(f'{MAILPIT_API}/chaos', data=body, method='PUT',
                                     headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(request).close()


def classify(error: Exception) -> tuple[str, str]:
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        code, text = next(iter(error.recipients.values()))
    elif isinstance(error, smtplib.SMTPResponseException):
        code, text = error.smtp_code, error.smtp_error
    else:
        return 'temporary', type(error).__name__        # обрыв, таймаут, отказ в соединении
    reason = f'{code} {text.decode(errors="replace")}'
    return ('temporary' if 400 <= code < 500 else 'permanent'), reason


def backoff(attempt: int, base: float = 60, cap: float = 3600) -> float:
    return random.uniform(0, min(cap, base * 2 ** attempt))   # экспонента с полным джиттером


def try_send(to: str) -> tuple[str, str]:
    message = EmailMessage()
    message['From'] = SENDER
    message['To'] = to
    message['Subject'] = 'Комментарий к задаче «Сдать отчёт»'
    message.set_content('Борис: черновик готов, посмотри, пожалуйста.')
    try:
        with connect() as smtp:
            smtp.send_message(message, from_addr=BOUNCE_ADDRESS)
    except (smtplib.SMTPException, OSError) as error:
        return classify(error)
    return 'sent', '250'


clear_mailbox()
outbox = {'anna@example.com': 0, 'boris@unknown.invalid': 0, 'vera@example.com': 0}
bad_addresses = set()

scenarios = [
    ('сервер недоступен', lambda: setattr(mailer, 'SMTP_PORT', 41099)),
    ('сервер перегружен, отвечает 451', lambda: (setattr(mailer, 'SMTP_PORT', 41025), set_chaos(451, 100))),
    ('сервер в порядке', lambda: set_chaos(451, 0)),
]
for title, prepare in scenarios:
    prepare()
    print(f'\nПроход: {title}')
    for address in list(outbox):
        status, reason = try_send(address)
        if status == 'sent':
            del outbox[address]
            print(f'  {address:<24} отправлено')
        elif status == 'permanent':
            del outbox[address]
            bad_addresses.add(address)
            print(f'  {address:<24} постоянная ошибка ({reason}) → адрес помечен, не повторяем')
        else:
            outbox[address] += 1
            delay = backoff(outbox[address])
            print(f'  {address:<24} временная ошибка ({reason}) → повтор через {delay:.0f} с')

print('\nв очереди:', outbox, '| плохие адреса:', bad_addresses)
print('в ящике Mailpit:', [m['To'][0]['Address'] for m in mailpit('/messages')['messages']])
