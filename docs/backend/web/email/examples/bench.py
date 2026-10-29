"""Сколько стоит соединение: новое на каждое письмо против одного переиспользуемого."""

import asyncio
import time
from email.message import EmailMessage

import aiosmtplib

from mailer import (BOUNCE_ADDRESS, SENDER, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER,
                    clear_mailbox, connect, mailpit, tls_context)

COUNT = 200


def letter(number: int) -> EmailMessage:
    message = EmailMessage()
    message['From'] = SENDER
    message['To'] = f'user{number}@example.com'
    message['Subject'] = f'Задача №{number} скоро просрочится'
    message.set_content(f'Срок задачи №{number} истекает завтра.')
    return message


def connection_per_letter() -> None:
    for number in range(COUNT):
        with connect() as smtp:
            smtp.send_message(letter(number), from_addr=BOUNCE_ADDRESS)


def one_connection() -> None:
    with connect() as smtp:
        for number in range(COUNT):
            smtp.send_message(letter(number), from_addr=BOUNCE_ADDRESS)


async def async_worker(numbers: range) -> None:
    async with aiosmtplib.SMTP(hostname=SMTP_HOST, port=SMTP_PORT, start_tls=True,
                               tls_context=tls_context(), username=SMTP_USER,
                               password=SMTP_PASSWORD) as smtp:
        for number in numbers:
            await smtp.send_message(letter(number), sender=BOUNCE_ADDRESS)


async def async_connections(workers: int) -> None:
    step = COUNT // workers
    await asyncio.gather(*(async_worker(range(i * step, (i + 1) * step)) for i in range(workers)))


runs = {
    'smtplib, соединение на письмо': connection_per_letter,
    'smtplib, одно соединение': one_connection,
    'aiosmtplib, одно соединение': lambda: asyncio.run(async_connections(1)),
    'aiosmtplib, 4 соединения параллельно': lambda: asyncio.run(async_connections(4)),
}
print(f'{COUNT} писем через STARTTLS + AUTH на локальный Mailpit\n')
started = time.perf_counter()
for _ in range(20):
    connect().quit()
print(f'установка соединения (TCP + EHLO + STARTTLS + AUTH): {(time.perf_counter() - started) / 20 * 1000:.0f} мс\n')
for name, run in runs.items():
    clear_mailbox()
    started = time.perf_counter()
    run()
    elapsed = time.perf_counter() - started
    delivered = mailpit('/messages?limit=1')['total']
    print(f'{name:<38} {elapsed:6.2f} с  {COUNT / elapsed:6.0f} писем/с  в ящике: {delivered}')
