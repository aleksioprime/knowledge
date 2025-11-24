# Установка Linux Ubuntu Server

1. Скачайте Ubuntu Server: https://ubuntu.com/download/server

2. Установите на сервер с подключённым интернетом (желательно, по LAN)

3. Выберите языковые настройки:
- Язык: Русский
- Layout: Russian
- Variant: Russian
- Shortcut: Alt+Shift

3. Оставьте выбор Ubuntu Server

4. Дождитесь, когда сетевое оборудование выдаст IP для сервера

5. Адрес прокси-сервера оставьте пустым

6. Дождитесь успешных тестов mirror location

7. Оставьте Use an entire disk жёсткий диск сервера и Set up this disk an LVM group

8. Заполните поля:
- Ваше имя: <введите ваше имя>, например Aleksei Semochkin
- Your servers name: <имя сервера>, например, aledev-home
- Введите имя пользователя: <логин>, например, alprime
- Задайте пароль: <пароль>, например, a13De$
- Подтвердите пароль: <пароль>

9. Для Upgrade to Ubuntu Pro выберите Skip for now

10. Выберите Install OpenSSH server

11. Дополнительные пакеты не выбирайте

12. Дождитесь окончания установки, после этого нажмите "Перезагрузить сейчас"

13. После сообщения Failed unmounting cdrom.mount извлеките флешку и нажмите Enter

14. После перезагрузки войдите в систему, введя логин и пароль

15. Обновите список пакетов и саму систему

```sh
sudo apt update && sudo apt upgrade -y
```
