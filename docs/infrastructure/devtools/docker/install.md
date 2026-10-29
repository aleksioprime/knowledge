# Установка Docker

## Установка на Ubuntu

Обновление списка пакетов:
```sh
sudo apt update
```

Установка утилит, необходимых для настройки репозитория
```sh
sudo apt install ca-certificates curl
```

Создание директории для хранения GPG-ключей репозиториев
```sh
sudo install -m 0755 -d /etc/apt/keyrings
```

Загрузка официального GPG-ключа Docker
```sh
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
```

Установка правильных прав на ключ
```sh
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Добавление официального Docker-репозитория:
```sh
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Обновление списка пакетов (теперь с новым репозиторием):
```sh
sudo apt update
```

Установка Docker:
```sh
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Дать права пользователю для обращения к Docker daemon:
```sh
sudo usermod -aG docker $USER
```
Переподключитесь по SSH

Проверка
```sh
docker run hello-world
```