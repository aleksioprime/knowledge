# Linux

**Linux** — семейство Unix-подобных операционных систем. На серверах — стандарт де-факто (Ubuntu, Debian, CentOS, Alpine). Уверенное владение базовыми операциями необходимо для бэкенд-разработки и DevOps.

Базовые навыки:
- Работа в терминале (`bash`/`zsh`), пайпы и редиректы
- Управление пользователями и правами (`chmod`, `chown`, `sudo`)
- Systemd-сервисы (`systemctl`)
- Сеть (`ip`, `ss`, `iptables`, `nftables`)
- Логи (`journalctl`, `tail -f`)
- Управление пакетами (`apt`, `dpkg`, `snap`)

## Содержание

- [Установка Ubuntu Server](ubuntu_install.md)
- [Настройка SSH](ssh_setup.md)
- [Подготовка VPS-сервера](prepare_server.md) — пользователь, SSH-ключи, UFW, Docker, swap и обслуживание
- [Настройка локального DNS](dns_local_setup.md)
- [Настройка WireGuard](wireguard_setup.md)

Установка NGINX на сервер описана в разделе [NGINX](../../backend/web/nginx/install.md).
