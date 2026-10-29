"""Ссылка подтверждения адреса: подписанный токен со сроком действия."""

import hashlib
import re
import time
from email.message import EmailMessage

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from mailer import BOUNCE_ADDRESS, SENDER, SITE_URL, clear_mailbox, connect, mailpit

SECRET_KEY = 'test-secret-key-only-for-example'
CONFIRM_MAX_AGE = 24 * 60 * 60

serializer = URLSafeTimedSerializer(SECRET_KEY)
users = {7: {'email': 'anna@example.com', 'email_verified': False}}


def email_fingerprint(email: str) -> str:
    # сам адрес в ссылку не кладём: payload читается без ключа и оседает в логах
    return hashlib.sha256(email.encode()).hexdigest()[:12]


def make_confirm_token(user_id: int) -> str:
    payload = {'uid': user_id, 'em': email_fingerprint(users[user_id]['email'])}
    return serializer.dumps(payload, salt='confirm-email')


def confirm_email(token: str, max_age: int = CONFIRM_MAX_AGE) -> str:
    try:
        data = serializer.loads(token, salt='confirm-email', max_age=max_age)
    except SignatureExpired:
        return 'ссылка устарела, отправьте письмо ещё раз'
    except BadSignature:
        return 'ссылка недействительна'
    user = users.get(data['uid'])
    if user is None or email_fingerprint(user['email']) != data['em']:
        return 'ссылка выдана для другого адреса'
    if user['email_verified']:
        return 'адрес уже подтверждён'
    user['email_verified'] = True
    return 'адрес подтверждён'


clear_mailbox()
token = make_confirm_token(7)
message = EmailMessage()
message['From'] = SENDER
message['To'] = users[7]['email']
message['Subject'] = 'Подтвердите адрес почты'
message.set_content(f'Чтобы подтвердить адрес, откройте ссылку:\n{SITE_URL}/confirm/{token}\n')
with connect() as smtp:
    smtp.send_message(message, from_addr=BOUNCE_ADDRESS)

text = mailpit(f"/message/{mailpit('/messages')['messages'][0]['ID']}")['Text']
link = re.search(r'https://\S+', text).group()
token_from_mail = link.rsplit('/', 1)[1]
print('ссылка из письма:', link)
print('длина токена:', len(token_from_mail))
print('payload без ключа:', serializer.loads_unsafe(token_from_mail, salt='confirm-email')[1])

print('\n1. переход по ссылке:', confirm_email(token_from_mail))
print('2. повторный переход:', confirm_email(token_from_mail))

payload, rest = token_from_mail.split('.', 1)
forged = serializer.dumps({'uid': 8, 'em': 'x'}, salt='other').split('.', 1)[0] + '.' + rest
print('3. подменённый payload:', confirm_email(forged))

reset_token = serializer.dumps({'uid': 7, 'em': email_fingerprint('anna@example.com')}, salt='reset-password')
print('4. токен сброса пароля вместо подтверждения:', confirm_email(reset_token))

users[7] = {'email': 'anna@example.com', 'email_verified': False}
old_token = make_confirm_token(7)
time.sleep(2)
print('5. через 2 секунды при сроке в 1 секунду:', confirm_email(old_token, max_age=1))

users[7]['email'] = 'anna.new@example.com'
print('6. адрес сменили после отправки письма:', confirm_email(old_token))
