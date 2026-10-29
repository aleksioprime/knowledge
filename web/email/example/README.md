# Письма из Python: стенд на Mailpit

Пример к заметке [Отправка email из Python-сервиса](../README.md). Вместо настоящего почтового сервера — [Mailpit](https://mailpit.axllent.org/): он принимает письма по SMTP, ничего никуда не пересылает и показывает их в веб-интерфейсе и через HTTP API. Скрипты проверяют результат через API, а не на глаз.

| Файл | Что внутри |
| --- | --- |
| [docker-compose.yaml](docker-compose.yaml) | Mailpit: SMTP с обязательным STARTTLS и любым логином, отказ (550) для адресов вне `example.com` и `tasker.test`, режим chaos для ошибок по заказу |
| [mailer.py](mailer.py) | настройки стенда, окружение Jinja2, сборка `EmailMessage`, подключение по SMTP, вызовы API Mailpit |
| [templates/](templates) | базовый шаблон (шапка, подвал с отпиской) и письмо «вам назначена задача» в HTML и текстовой версии |
| [smtp_dialog.py](smtp_dialog.py) | команды SMTP по шагам и ответы сервера |
| [send_task_assigned.py](send_task_assigned.py) | рендер шаблона, `multipart/alternative`, `List-Unsubscribe`, отправка и проверка через API |
| [sandbox.py](sandbox.py) | проверка шаблонов менеджеров в `SandboxedEnvironment` и попытки выбраться из песочницы |
| [confirm_token.py](confirm_token.py) | ссылка подтверждения адреса на `itsdangerous`: срок, подделка, повторный переход |
| [bench.py](bench.py) | 200 писем: соединение на письмо против одного соединения, `smtplib` и `aiosmtplib` |
| [errors.py](errors.py) | временные и постоянные ошибки, повтор с паузой и пометка плохого адреса |

Логин, пароль и секретный ключ в скриптах **только тестовые**: Mailpit принимает любые.

## Запуск

```bash
docker compose -p kb-mail up -d          # SMTP на localhost:41025, интерфейс на http://localhost:48025
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python smtp_dialog.py
python send_task_assigned.py
python sandbox.py                        # Mailpit не нужен
python confirm_token.py
python bench.py
python errors.py
```

Каждый скрипт, кроме `sandbox.py`, сначала очищает ящик Mailpit. Письма можно посмотреть в браузере на http://localhost:48025 или через API:

```bash
curl -s localhost:48025/api/v1/messages | python -m json.tool | head -30
curl -s localhost:48025/api/v1/message/<ID>            # тема, From, Text, HTML
curl -s localhost:48025/api/v1/message/<ID>/headers    # все заголовки
```

Остановить и удалить данные:

```bash
docker compose -p kb-mail down -v
```

Вывод скриптов и разбор — в [заметке](../README.md).

## Особенности стенда

- Mailpit сам выпускает самоподписанный сертификат (`sans:localhost`), поэтому `mailer.tls_context()` отключает проверку сертификата. С настоящим сервером используйте `ssl.create_default_context()` без изменений.
- Порты открыты только на `127.0.0.1`: API Mailpit без пароля отдаёт все письма.
- Режим chaos (`MP_ENABLE_CHAOS`) включает ошибки через `PUT /api/v1/chaos`; `errors.py` в конце выключает их обратно.
