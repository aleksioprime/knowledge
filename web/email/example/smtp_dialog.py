"""SMTP по шагам: какие команды отправляет клиент и что отвечает сервер."""

import smtplib

from mailer import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER, clear_mailbox, mailpit, tls_context

clear_mailbox()
smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)


def show(command: str, reply: tuple[int, bytes]) -> None:
    code, text = reply
    print(f'{command:<36} → {code} {text.decode().splitlines()[0]}')


show('EHLO tasker.test', smtp.ehlo('tasker.test'))
show('MAIL FROM:<bounces@tasker.test>', smtp.mail('bounces@tasker.test'))
show('STARTTLS', smtp.starttls(context=tls_context()))
show('EHLO tasker.test (уже внутри TLS)', smtp.ehlo('tasker.test'))
show('AUTH PLAIN ...', smtp.login(SMTP_USER, SMTP_PASSWORD))
show('MAIL FROM:<bounces@tasker.test>', smtp.mail('bounces@tasker.test'))
show('RCPT TO:<anna@example.com>', smtp.rcpt('anna@example.com'))
show('RCPT TO:<boris@unknown.invalid>', smtp.rcpt('boris@unknown.invalid'))
body = (
    'From: =?utf-8?b?0JfQsNC00LDRh9C90LjQug==?= <notify@tasker.test>\r\n'
    'To: anna@example.com\r\n'
    'Subject: Ping\r\n'
    '\r\n'
    'Hello from SMTP dialog.\r\n'
)
show('DATA ... .', smtp.data(body))
show('QUIT', smtp.quit())

message = mailpit('/messages')['messages'][0]
headers = mailpit(f"/message/{message['ID']}/headers")
print('\nзаголовок From:', message['From']['Name'], message['From']['Address'])
print('конверт (Return-Path):', headers['Return-Path'][0])
print('получатели:', [to['Address'] for to in message['To']])
