# Локальный DNS

## Настройка доступа локального сервера по локальной сети по адресу `demo.local`:

Посмотрите текущее имя хоста:
```sh
hostnamectl
```

Если нужно изменить на `demo`:
```sh
sudo hostnamectl set-hostname demo
sudo reboot
```

Установите Avahi:
```sh
sudo apt update
sudo apt install avahi-daemon -y
```

Включите и запустите демон `avahi`:
```sh
sudo systemctl enable avahi-daemon --now
```

Проверьте статус демона `avahi`:
```sh
systemctl status avahi-daemon
```

## Настройка локального DNS-сервера

Установите DNS-сервер
```sh
sudo apt update
sudo apt install dnsmasq -y
```

После установки dnsmasq уже автоматически запустится. Проверьте статус:
```sh
systemctl status dnsmasq
```

Создайте локальный домен:
```sh
echo "address=/demo.local/192.168.1.105" | sudo tee /etc/dnsmasq.d/demo.conf
sudo systemctl restart dnsmasq
```

Добавьте DNS-сервер в роутер:

Зайдите в настройки роутера → DHCP / LAN → DNS settings и установите `Primary DNS: 192.168.1.105` (Если не работает — можно добавить как Secondary DNS)

Проверьте доступ на сервере и извне:
```sh
ping demo.local
```

Пример добавления других доменов:
```sh
echo "address=/api.local/192.168.1.105" | sudo tee /etc/dnsmasq.d/api.conf
echo "address=/frontend.local/192.168.1.105" | sudo tee /etc/dnsmasq.d/frontend.conf
sudo systemctl restart dnsmasq
```
