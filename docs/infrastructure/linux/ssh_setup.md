# Настройка подключения по SSH

Проверьте работу SSH сервера:
```sh
sudo systemctl status ssh
```

Если в поле Active стоит inactive (dead), активируйте работу службы:
```sh
sudo systemctl enable ssh
```

Перезапустите службу:
```sh
sudo systemctl restart ssh
```

## Установка SSH-ключа

Сгенерируйте ключ на локальном компьютере (команду выполнять на локальной машине)
```sh
ssh-keygen -t rsa -b 4096 -f ~/.ssh/aledev_home
```

Добавьте ключ на домашний сервер (команду выполнять на локальной машине):
```sh
ssh-copy-id -i ~/.ssh/aledev_home <username>@192.168.xx.xx
```

После этого введите `yes` и введите пароль пользователя <username>

Проверьте подключение по ключу
```sh
ssh -i ~/.ssh/aledev_home <username>@192.168.xx.xx
```

Отключите вход на домашний сервер по паролю. Откройте файл:
```sh
sudo nano /etc/ssh/sshd_config
```

Добавьте/измените строки:
```
PasswordAuthentication no
PubkeyAuthentication yes
```

Иногда другие файлы могут перебивать эти настройки. Найдите их:
```sh
sudo grep -r PasswordAuthentication /etc/ssh/sshd_config.d/
```

Например, найден:
/etc/ssh/sshd_config.d/50-cloud-init.conf:PasswordAuthentication yes

Откройте найденный файл:
```sh
sudo nano /etc/ssh/sshd_config.d/50-cloud-init.conf
```

Измените строку:
```
PasswordAuthentication no
```

Перезагрузите SSH:
```sh
sudo systemctl restart ssh
```

Проверьте применённую настройку:
```sh
sudo sshd -T | grep passwordauthentication
```

Если видишь: `passwordauthentication no` - всё применилось правильно.

## Настройка файервола

UFW (Uncomplicated Firewall) — это упрощённый интерфейс для управления встроенным в Linux файерволом iptables / nftables. Он нужен для контроля входящих и исходящих сетевых соединений, чтобы защитить сервер или компьютер от нежелательного доступа.

Установите разрешения до включения файервола:
```sh
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
```

Включите файервол:
```sh
sudo ufw enable
```

Проверьте статус
```sh
sudo ufw status
```

Для отключения используется команда:
```sh
sudo ufw disable
```

Для удаления правила используется команда:
```sh
sudo ufw delete allow 9000
```
