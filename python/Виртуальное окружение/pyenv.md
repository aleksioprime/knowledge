Это инструмент для управления версиями Python. Он позволяет устанавливать, переключаться и управлять разными версиями Python на одном компьютере **без влияния на системную версию**
# Установка pyEnv

Информация по установке: https://github.com/pyenv/pyenv
## Установка в ОС Linux

Установите `pyenv`:
```sh
curl -fsSL https://pyenv.run | bash
```

Добавьте настройки в среду оболочки `bash`:
```sh
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --patch)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
```

Либо сделайте это вручную. Для этого откройте файл `bashrc`:
```sh
sudo nano ~/.bashrc
```
И добавьте в конец файла следующие строчки:
```
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"
```

Примените изменения:
```sh
source ~/.bashrc
```

Проверьте версию pyenv:
```sh
pyenv --version
```

## Установка в MacOS

Для установки используется менеджер пакетов [homebrew](https://brew.sh/)

Обновите `homebrew` и с его помощью установите `pyenv` и плагин поддержки виртуальных окружения `pyenv-virtualenv`:
```sh
brew update
brew install pyenv
brew install pyenv-virtualenv
```

Добавьте настройки в среду оболочки `zsh`:
```sh
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc 
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
```

Перезапустите оболочку

# Создание виртуальной среды

Проверьте версию и установленные плагины:
```shell
pyenv --version
pyenv virtualenvs
```

Установите нужную версию Python
```sh
pyenv install 3.12.11
```

Создайте виртуальное окружение:
```shell
pyenv virtualenv 3.12.11 name_venv
```

Активация виртуального окружения:
```shell
pyenv activate name_venv
```

Выход из виртуального окружения:
```shell
pyenv deactivate
```