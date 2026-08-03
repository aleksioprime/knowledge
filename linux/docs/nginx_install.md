## Установка NGINX

Здесь описаны установка пакета и создание первого сайта на Ubuntu. Reverse proxy, TLS, балансировка и ограничения разобраны в разделе [NGINX](../../web/nginx/README.md).

Обновите пакеты Ubuntu:
```sh
sudo apt update
```

Установите NGINX:
```sh
sudo apt install nginx -y
```

Проверяем статус службы:
```sh
systemctl status nginx
```

Проверка внутри сервера:
```sh
curl http://localhost
```

Настройте файервол и проверьте:
```sh
sudo ufw allow 'Nginx Full'
sudo ufw status
```

## Структура конфигурации

Конфигурации сайтов описываются в файлах по пути:
```sh
/etc/nginx/sites-available/
```

Симлинки на сайты создаются по пути:
```sh
/etc/nginx/sites-enabled/
```

Глобальный конфиг находится по пути:
```sh
/etc/nginx/nginx.conf
```

Статичные файлы находятся по пути (по умолчанию):
```sh
/var/www/html/
```

## Создание demo-сайта

### Подготовка файлов

Создайте папку:
```sh
sudo mkdir -p /var/www/demo.local
sudo chown -R $USER:$USER /var/www/demo.local
```

Создайте/скопируйте файлы сайта:
```sh
echo "<h1>Hello from Demo</h1>" > /var/www/demo.local/index.html
```

### Создание конфигурации

Создайте файл:
```sh
sudo nano /etc/nginx/sites-available/demo.local
```

Опишите настройки:
```
server {
    listen 80;
    listen [::]:80;

    server_name demo.local;

    root /var/www/demo.local;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

### Запуск demo-сайта

Активируйте сайт:
```sh
sudo ln -s /etc/nginx/sites-available/demo.local /etc/nginx/sites-enabled/
```

Проверьте синтаксис:
```sh
sudo nginx -t
```

Перезапустите `nginx` для применения конфигураций:
```sh
sudo systemctl reload nginx
```

Проверка внутри сервера:
```sh
curl http://demo.local
```

## Логи NGINX

Логи ошибок
```sh
sudo tail -f /var/log/nginx/error.log
```

Логи доступа:
```sh
sudo tail -f /var/log/nginx/access.log
```

Для выхода нажмите Ctrl + C

## Доступ извне через облако Keenetic

1. Зайди в веб-интерфейс роутера и перейдите в меню `Сетевые правила` -> `Доменное имя`

2. В разделе `Доступ к веб-приложениям домашней сети` добавьте настройку доступа, указав:
- укажите имя поддомена вашего устройства (например, demo.alprime.keenetic.pro)
- Доступ из интернета: Свободный доступ;
- Устройство: выберите зарегистрированое подключенное к сети устройство;
- Протокол: HTTP
- Порт TCP: 81

3. Добавьте порт `81` в прослушиваемые в конфигурации nginx вашего сайта:

```sh
sudo nano /etc/nginx/sites-available/demo.local
```

```
server {
    listen 80;
    listen [::]:80;

    listen 81;
    listen [::]:81;

    server_name demo.local;

    root /var/www/demo.local;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```
