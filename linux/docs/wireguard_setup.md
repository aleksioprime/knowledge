# Установка и настройка WireGuard

WireGuard — это современный VPN-протокол, ориентированный на минимализм, высокую скорость работы и безопасность. Он использует небольшой кодовой базис, криптографию последнего поколения (Curve25519, ChaCha20, Poly1305, BLAKE2s) и работает в пространстве ядра Linux, что обеспечивает низкие задержки и высокую пропускную способность. Конфигурация WireGuard состоит только из двух сущностей: Interfaces (интерфейсы) и Peers (узлы). Между узлами устанавливается зашифрованный туннель, в рамках которого передаются IP-пакеты.

WireGuard не требует сложного управления сертификатами. Каждый узел имеет пару ключей (private/public) и списки разрешённых адресов (AllowedIPs), на основании которых происходит маршрутизация трафика внутри туннеля.

## Установка и настройка WireGuard на VPS

### Установка WireGuard

```bash
sudo apt update
sudo apt install wireguard
```

### Генерация ключей сервера

```bash
wg genkey | sudo tee /etc/wireguard/server_private.key | wg pubkey | sudo tee /etc/wireguard/server_public.key
```

### Создание конфигурации сервера

```bash
sudo nano /etc/wireguard/wg0.conf
```

Пример конфигурации:

```ini
[Interface]
Address = 10.10.10.1/24
ListenPort = 51820
PrivateKey = <SERVER_PRIVATE_KEY>
SaveConfig = true
```

Содержимое `<SERVER_PRIVATE_KEY>` берётся из файла `/etc/wireguard/server_private.key`.

### Настройка межсетевого экрана

```bash
sudo ufw allow 51820/udp
```

### Разрешение маршрутизации

Открыть файл:

```bash
sudo nano /etc/sysctl.conf
```

Разкомментировать строку:

```
net.ipv4.ip_forward=1
```

Применить настройки:

```bash
sudo sysctl -p
```

### Запуск WireGuard

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

Проверка состояния:

```bash
sudo wg show
```

---

## Добавление Keenetic Ultra как WireGuard-клиента

### Генерация ключей для Keenetic

На VPS:

```bash
wg genkey | tee keenetic_private.key | wg pubkey | tee keenetic_public.key
```

### Добавление Peer в конфигурацию сервера

Открыть конфигурацию:

```bash
sudo nano /etc/wireguard/wg0.conf
```

Добавить:

```ini
[Peer]
PublicKey = <KEENETIC_PUBLIC_KEY>
AllowedIPs = 10.10.10.2/32, 192.168.2.0/24
```

- `10.10.10.2/32` — IP Keenetic внутри VPN-туннеля.
- `192.168.2.0/24` — домашняя сеть, которую необходимо маршрутизировать через туннель.

Перезапустить сервер:

```bash
sudo systemctl restart wg-quick@wg0
```

---

## Настройка WireGuard-клиента на Keenetic Ultra

Открыть интерфейс устройства и перейти:

```
Другие подключения → WireGuard → Добавить подключение
```

Параметры:

**Имя подключения:**

```
VPS-WG
```

**Адрес интерфейса:**

```
10.10.10.2/32
```

**Ключи:**

- Сгенерировать пару ключей в интерфейсе Keenetic.
- Публичный ключ Keenetic вставить в конфигурацию VPS.
- Приватный ключ хранится лишь в роутере.

**Endpoint:**

```
<VPS_PUBLIC_IP>:51820
```

**Allowed IPs:**

Для доступа только к домашней сети:

```
192.168.2.0/24
```

Для маршрутизации всего трафика:

```
0.0.0.0/0
```

Включить:

```
Разрешить доступ к домашней сети
```

---

## Проверка соединения

На VPS:

```bash
sudo wg show
```

На клиенте:

```bash
ping 192.168.2.105
ssh <user>@192.168.2.105
```

---

## Добавление дополнительных клиентов

### Генерация ключей

```bash
wg genkey | tee laptop_private.key | wg pubkey | tee laptop_public.key
```

### Добавление Peer на сервере

```ini
[Peer]
PublicKey = <LAPTOP_PUBLIC_KEY>
AllowedIPs = 10.10.10.3/32
```

Перезапуск:

```bash
sudo systemctl restart wg-quick@wg0
```

### Конфигурация клиента

```ini
[Interface]
PrivateKey = <LAPTOP_PRIVATE_KEY>
Address = 10.10.10.3/32
DNS = 1.1.1.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
Endpoint = <VPS_PUBLIC_IP>:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

---

## Заключение

WireGuard-сервер на VPS в сочетании с Keenetic Ultra в роли клиента позволяет получить постоянный безопасный доступ ко всем ресурсам домашней сети без необходимости иметь публичный IP-адрес дома или выполнять проброс портов. Такой туннель обеспечивает высокую производительность, безопасность и надёжность.