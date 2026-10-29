# Подготовка VPS-сервера на Ubuntu

- `<server_ip>` - публичный IP-адрес VPS
- `<username>` - имя пользователя на сервере
- `<ssh_key>` - имя SSH-ключа на локальном компьютере

## Первое подключение

Подключитесь к серверу по паролю, который выдал VPS-провайдер:

```sh
ssh root@<server_ip>
```

Если провайдер уже создал обычного пользователя:

```sh
ssh <username>@<server_ip>
```

Проверьте версию системы:

```sh
lsb_release -a
```

## Изменение hostname

Посмотрите текущий hostname:

```sh
hostnamectl
```

Задайте новое имя сервера:

```sh
sudo hostnamectl set-hostname <hostname>
# например, sudo hostnamectl set-hostname app-vps
```

Откройте файл `/etc/hosts`:

```sh
sudo nano /etc/hosts
```

Найдите строку со старым hostname и замените его на новый. Обычно достаточно такой структуры:

```hosts
127.0.0.1 localhost
127.0.1.1 app-vps
```

Проверьте результат:

```sh
hostnamectl
hostname
```

Если имя в терминале не изменилось сразу, переподключитесь по SSH:

## Обновление системы

Обновите список пакетов и установите обновления:

```sh
sudo apt update
sudo apt upgrade -y
```

Установите базовые утилиты:

```sh
sudo apt install -y curl wget git nano htop ca-certificates gnupg lsb-release unzip ufw
```

Если после обновления требуется перезагрузка:

```sh
sudo reboot
```

## Создание пользователя

Если вы подключились под `root`, создайте отдельного пользователя:

```sh
adduser <username>
```

Добавьте пользователя в группу `sudo`:

```sh
usermod -aG sudo <username>
```

Проверьте вход под новым пользователем с локального компьютера:

```sh
ssh <username>@<server_ip>
```

Проверьте права `sudo`:

```sh
sudo whoami
```

Команда должна вывести:

```sh
root
```

## Настройка SSH-ключа

На локальном компьютере сгенерируйте ключ:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/<ssh_key>
```

Если нужен RSA-ключ для старых систем:

```sh
ssh-keygen -t rsa -b 4096 -f ~/.ssh/<ssh_key>
```

Скопируйте публичный ключ на сервер:

```sh
ssh-copy-id -i ~/.ssh/<ssh_key>.pub <username>@<server_ip>
```

Если `ssh-copy-id` недоступен, ключ можно добавить вручную.

На локальном компьютере выведите публичный ключ:

```sh
cat ~/.ssh/<ssh_key>.pub
```

Скопируйте всю строку, которая начинается с `ssh-ed25519` или `ssh-rsa`.

На сервере создайте папку `.ssh` и файл `authorized_keys`:

```sh
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
```

Вставьте публичный ключ в файл отдельной строкой, сохраните файл и закройте редактор.

Выставьте правильные права:

```sh
chmod 600 ~/.ssh/authorized_keys
```

Проверьте подключение по ключу:

```sh
ssh -i ~/.ssh/<ssh_key> <username>@<server_ip>
```

Не закрывайте текущую SSH-сессию, пока не проверите вход по ключу в новом окне терминала.

## Отключение входа по паролю

Перед этим шагом должен работать вход по SSH-ключу для обычного пользователя с `sudo`. Старую SSH-сессию не закрывайте до финальной проверки.

Откройте основной конфиг SSH:

```sh
sudo nano /etc/ssh/sshd_config
```

Добавьте или измените строки:

```conf
PubkeyAuthentication yes
PasswordAuthentication no
PermitRootLogin prohibit-password
```

На облачных образах Ubuntu настройки могут переопределяться файлами в `/etc/ssh/sshd_config.d/`. Проверьте:

```sh
sudo grep -R "PasswordAuthentication\|PermitRootLogin" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/
```

Если найден файл вроде `/etc/ssh/sshd_config.d/50-cloud-init.conf`, откройте его:

```sh
sudo nano /etc/ssh/sshd_config.d/50-cloud-init.conf
```

И установите:

```conf
PasswordAuthentication no
```

Проверьте итоговую конфигурацию:

```sh
sudo sshd -t
```

Перезапустите SSH:

```sh
sudo systemctl restart ssh
```

Проверьте применённые настройки:

```sh
sudo sshd -T | grep -E "passwordauthentication|permitrootlogin|pubkeyauthentication"
```

Ожидаемый результат:

```sh
passwordauthentication no
permitrootlogin no
pubkeyauthentication yes
```

Снова проверьте вход по ключу с локального компьютера:

```sh
ssh -i ~/.ssh/<ssh_key> <username>@<server_ip>
```

## Настройка UFW

Перед включением файервола обязательно разрешите SSH:

```sh
sudo ufw allow OpenSSH
```

Разрешите HTTP и HTTPS для веб-приложений:

```sh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Если у приложения есть отдельный порт, например `3000`, откройте его только при необходимости:

```sh
sudo ufw allow 3000/tcp
```

Включите UFW:

```sh
sudo ufw enable
```

Проверьте статус:

```sh
sudo ufw status verbose
```

Удалить правило можно так:

```sh
sudo ufw delete allow 3000/tcp
```

Важно: Docker сам управляет правилами iptables. Если контейнер опубликован через `ports`, этот порт может быть доступен извне даже при закрытом UFW. Для публичных сервисов лучше публиковать только `80`/`443` через NGINX или другой reverse proxy.

## Установка Docker

```sh
curl -fsSL https://get.docker.com | sh
```

### Ручная установка Docker

Удалите конфликтующие старые пакеты, если они были установлены:

```sh
sudo apt remove -y docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc
```

Добавьте официальный GPG-ключ Docker:

```sh
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Добавьте официальный репозиторий Docker:

```sh
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Узнать кодовое имя Ubuntu:

```sh
. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}
```

Узнать архитектуру:

```sh
dpkg --print-architecture
```

Например, для Ubuntu 24.04 на обычном VPS:

```deb822
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
```

Обновите список пакетов:

```sh
sudo apt update
```

Установите Docker Engine, Buildx и Docker Compose plugin:

```sh
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Проверьте службу Docker:

```sh
sudo systemctl status docker
```

Если служба не запущена:

```sh
sudo systemctl enable docker
sudo systemctl start docker
```

Проверьте установку:

```sh
sudo docker run hello-world
```

Проверьте Docker Compose:

```sh
docker compose version
```

## Запуск Docker без sudo

Добавьте пользователя в группу `docker`:

```sh
sudo usermod -aG docker $USER
```

Примените новую группу без перезахода:

```sh
newgrp docker
```

Проверьте запуск без `sudo`:

```sh
docker run hello-world
```

Если команда не работает, выйдите из SSH-сессии и подключитесь заново:

```sh
exit
ssh -i ~/.ssh/<ssh_key> <username>@<server_ip>
```

## Настройка автозапуска Docker

Включите автозапуск Docker и containerd:

```sh
sudo systemctl enable docker
sudo systemctl enable containerd
```

Проверьте:

```sh
systemctl is-enabled docker
systemctl is-enabled containerd
```

## Проверка ресурсов сервера

Проверьте свободное место:

```sh
df -h
```

Проверьте память:

```sh
free -h
```

Проверьте нагрузку:

```sh
uptime
```

Проверьте открытые порты:

```sh
sudo ss -tulpn
```

## Настройка swap

Для маленьких VPS на 1-2 GB RAM полезно добавить swap-файл.

Создайте swap на 2 GB:

```sh
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

Добавьте автоподключение swap:

```sh
echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
```

Проверьте:

```sh
free -h
```

## Обновление Docker и системы

Периодическое обновление:

```sh
sudo apt update
sudo apt upgrade -y
```

После обновления Docker проверьте версии:

```sh
docker version
docker compose version
```

Если обновлялось ядро или системные службы:

```sh
sudo reboot
```

## Очистка Docker

Посмотреть занятое место:

```sh
docker system df
```

Удалить неиспользуемые контейнеры, сети, образы и build cache:

```sh
docker system prune
```

Удалить также неиспользуемые volume:

```sh
docker system prune --volumes
```

Команды очистки используйте внимательно: volume могут содержать данные баз данных и загруженные пользователями файлы.

## Финальная проверка

Проверьте SSH:

```sh
ssh -i ~/.ssh/<ssh_key> <username>@<server_ip>
```

Проверьте UFW:

```sh
sudo ufw status verbose
```

Проверьте Docker:

```sh
docker run hello-world
docker compose version
```

Проверьте автозапуск:

```sh
systemctl is-enabled ssh
systemctl is-enabled docker
systemctl is-enabled containerd
```

После этого сервер готов для запуска приложений через Docker Compose.
