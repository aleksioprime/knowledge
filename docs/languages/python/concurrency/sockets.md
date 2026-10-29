# Сокеты

Сокеты нужны, когда двум программам надо обмениваться данными напрямую: веб-серверу и браузеру, клиенту и базе данных, двум сервисам на одной машине. Всё, что выше, — HTTP, фреймворки, драйверы — построено поверх сокетов, поэтому знание `socket` и `selectors` помогает читать сетевые ошибки и писать собственные серверы.

::: warning Примеры с сокетами запускайте локально
В браузере у Python нет сетевых сокетов, поэтому под кодом показан вывод, полученный при локальном запуске.
:::

## Минимальный пример

Сервер и клиент в одном скрипте: сервер слушает свободный порт на `localhost`, клиент подключается, отправляет запрос и получает ответ.

```python
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('127.0.0.1', 0))  # порт 0: ОС выберет свободный
server.listen()
port = server.getsockname()[1]

client = socket.create_connection(('127.0.0.1', port))
conn, address = server.accept()

client.sendall(b'order 42')
request = conn.recv(1024)
conn.sendall(b'accepted: ' + request)
print(client.recv(1024))  # b'accepted: order 42'

for sock in (client, conn, server):
    sock.close()
```

## Как это работает

Сокет — программный интерфейс (endpoint) для обмена данными между процессами по сети или внутри одной машины.

Сокеты упрощают передачу сообщений: вся логика работы с сетью и передачи пакетов спрятана внутри них.

Внутри системы каждый IP-адрес принадлежит какому-нибудь сетевому интерфейсу. Интерфейсы бывают:

- **Физические.** Сетевые порты, Wi-Fi-адаптеры и другие устройства. В Linux они обычно называются `eno1`, `enp0s3` для Ethernet и `wlan0` или `wlp5s0` для Wi-Fi.
- **Виртуальные.** Существуют только на уровне ОС и не привязаны к физическому адаптеру. Основной виртуальный интерфейс — петлевой (loopback). Через него процессы обмениваются данными внутри одного компьютера. Он использует подсеть `127.0.0.0/8` (адреса от `127.0.0.0` до `127.255.255.255`). Такие соединения видны только внутри компьютера и недоступны внешним клиентам. В этот диапазон входит и `localhost` (`127.0.0.1`) — адрес обратной связи с компьютером.

### HTTP-сервер на сокетах

Простой HTTP-сервер, который обрабатывает запросы в одном потоке. Откройте в браузере `http://localhost:8888/` — сервер вернёт текст запроса, который вы отправили. Или выполните в терминале `curl -X POST http://localhost:8888/`.

```python
import socket

HOST, PORT = '', 8888


def handle_request(request: bytes) -> bytes:
    """
    Декодирует байты запроса в строку, формирует HTTP-ответ
    с текстом запроса и возвращает его в виде байтов
    """
    request_data = request.decode()
    http_response = f"""HTTP/1.1 200 OK\nContent-Type: text/html\n\n{request_data}"""
    return http_response.encode()


def serve_forever():
    # Создаём сокет: AF_INET — адресация IPv4, SOCK_STREAM — протокол TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listen_socket:
        # SO_REUSEADDR позволяет повторно использовать адрес сразу после закрытия сокета
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        # Привязываем сокет к адресу и порту
        listen_socket.bind((HOST, PORT))
        # Переводим сокет в режим прослушивания
        listen_socket.listen()
        print(f'Serving HTTP on port {PORT} ...')

        while True:
            # Ждём подключения клиента: получаем соединение и адрес
            client_connection, client_address = listen_socket.accept()
            with client_connection:
                # Получаем данные от клиента пачками по 1024 байта
                request = client_connection.recv(1024)
                http_response = handle_request(request)
                client_connection.sendall(http_response)


if __name__ == '__main__':
    try:
        serve_forever()
    except KeyboardInterrupt:
        print('\nСервер остановлен пользователем')
```

```text
Serving HTTP on port 8888 ...

Сервер остановлен пользователем
```

### Селектор: много клиентов в одном потоке

Сокет работает через файловый дескриптор — число, которое ОС выдаёт процессу для работы с ресурсом ввода-вывода. Портов может не хватить: их максимум 65535. Поэтому включают опцию переиспользования адреса, которая позволяет подключить больше клиентов, чем портов: число файловых дескрипторов не ограничено количеством портов.

Под капотом сокеты работают с событиями операционной системы. Можно создать много сокетов и опрашивать их по кругу, но при большом числе соединений это неэффективно. Нагрузку на ОС снижает поллинг (polling) — отслеживание новых событий ОС и реакция на них.

Часть программы, которая обрабатывает события сокетов от ОС, называется селектором. Он позволяет в одном потоке ждать событий сразу от нескольких файловых дескрипторов.

У селектора два основных события:

- `EVENT_READ` (1) — в сокете есть данные для чтения;
- `EVENT_WRITE` (2) — сокет готов к записи данных.

Пример — TCP-сервер, который обслуживает нескольких клиентов в одном потоке. Для проверки выполните `curl -X POST http://localhost:8000/`: сервер вернёт текст вашего запроса.

```python
import logging
import selectors
import socket
import sys

HOST, PORT = '', 8000

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


def new_connection(selector: selectors.BaseSelector, sock: socket.socket):
    """
    Обрабатывает новое входящее соединение.
    Вызывается, когда на серверном сокете происходит событие чтения — кто-то подключается к серверу
    """
    # Для общения с клиентом создаётся новый сокет
    new_conn, address = sock.accept()
    logger.info('accepted new_conn from %s', address)
    new_conn.setblocking(False)

    # Регистрируем клиентский сокет в селекторе: ждём, когда клиент пришлёт данные
    selector.register(new_conn, selectors.EVENT_READ, read_callback)


def read_callback(selector: selectors.BaseSelector, sock: socket.socket):
    """Обрабатывает событие чтения на клиентском сокете — клиент прислал данные."""
    data = sock.recv(1024)
    if data:
        # Отправляем полученные данные обратно
        sock.send(data)
    else:
        # Данных нет — клиент закрыл соединение: убираем сокет из селектора и закрываем его
        logger.info('closing connection %s', sock)
        selector.unregister(sock)
        sock.close()


def run_iteration(selector: selectors.BaseSelector):
    """Одна итерация обработки событий в селекторе."""
    # Список событий на зарегистрированных сокетах
    events = selector.select()
    for key, mask in events:
        # Callback, зарегистрированный вместе с сокетом:
        # new_connection для серверного сокета и read_callback для клиентского
        callback = key.data
        callback(selector, key.fileobj)


def serve_forever():
    """Запускает сервер на постоянное прослушивание новых сообщений."""
    # Селектор — системный механизм ожидания готовности файловых дескрипторов
    with selectors.SelectSelector() as selector:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
            server_socket.bind((HOST, PORT))
            server_socket.listen()
            # Неблокирующий режим: ожидание соединений не останавливает программу
            server_socket.setblocking(False)
            logger.info('Server started on port %s', PORT)

            # Новые соединения на серверном сокете обрабатывает new_connection
            selector.register(server_socket, selectors.EVENT_READ, new_connection)

            while True:
                run_iteration(selector)


if __name__ == '__main__':
    try:
        serve_forever()
    except KeyboardInterrupt:
        print('\nСервер остановлен пользователем')
```

```text
Server started on port 8000

Сервер остановлен пользователем
```

## Частые ошибки

- Перезапуск сервера сразу после остановки → `OSError: [Errno 48] Address already in use`: порт ещё в состоянии `TIME_WAIT` → выставлять `SO_REUSEADDR` до `bind()`.
- `recv(1024)` считают одним сообщением → длинный запрос приходит кусками, а два коротких склеиваются в один → читать в цикле до пустых данных или разделителя либо передавать длину сообщения в заголовке.
- `send()` вместо `sendall()` → отправлена только часть буфера, клиент получает обрезанный ответ → использовать `sendall()` или проверять возвращённое число байт в цикле.
- Блокирующие `accept()` и `recv()` в сервере на несколько клиентов → пока один клиент молчит, остальные ждут → перевести сокеты в неблокирующий режим и ждать события через `selectors` либо взять `asyncio`.
- Соединение не закрыто после обработки → утечка файловых дескрипторов, со временем `OSError: Too many open files` → работать с сокетом через `with` и снимать его с регистрации в селекторе перед `close()`.

## Когда не использовать

Если нужен HTTP, не пишите разбор запросов на сокетах: возьмите `http.server` для простого случая или фреймворк (FastAPI, aiohttp) для настоящего сервиса. Они обрабатывают заголовки, кодировки, keep-alive и ошибки, которые в примерах выше опущены. Для клиента то же самое: `httpx`, `requests` или `aiohttp` вместо ручных `connect` и `send`.

Селектор с коллбэками вручную тоже редко нужен: при десятках соединений та же схема уже готова в [asyncio](async.md) — с корутинами вместо коллбэков, таймерами, отменой и TLS в комплекте.

## Связанные темы

- [Многозадачность в Python](README.md)
- [Цикл событий своими руками](event_loop.md) — тот же селектор внутри самодельного планировщика
- [Асинхронность (asyncio)](async.md)
