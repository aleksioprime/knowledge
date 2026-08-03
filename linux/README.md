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

- [Установка Ubuntu Server](docs/ubuntu_install.md)
- [Настройка SSH](docs/ssh_setup.md)
- [Установка NGINX на Ubuntu](docs/nginx_install.md) — установка пакета и первый сайт; основные сценарии находятся в разделе [Веб-протоколы и инфраструктура](../web/nginx/README.md)
- [Настройка локального DNS](docs/dns_local_setup.md)
- [Настройка WireGuard](docs/wireguard_setup.md)
