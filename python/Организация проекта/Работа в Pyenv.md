## Установка `pyenv` на MacOS

Источник: https://github.com/pyenv/pyenv

Установите **pyenv**:

```sh
brew update
brew install pyenv
brew install pyenv-virtualenv
```

Дополнительно нужно установить lzma:

```sh
brew install xz
```

Добавьте настройки в zsh (при необходимости):

```sh
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init - zsh)"' >> ~/.zshrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
```

## Установка `pyenv` на Linux

Установите **pyenv**:

```sh
curl -fsSL https://pyenv.run | bash
```

Добавьте настройки в bash

```python
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
```

Альтернативный вариант. Откройте файл для редактирования:

```shell
sudo nano ~/.bashrc
```

Вставьте в конец файла следующие строчки:

```
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"
```

Примените изменения:

```shell
source ~/.bashrc
```

## Проверка установки

Проверьте версию pyenv:

```shell
pyenv --version
```

## Установка и работа со средой

Установите нужную версию Python

```
pyenv install 3.12.10
```

Создайте виртуальную среду

```
pyenv virtualenv 3.12.10 demo
```

Запуск среды

```
pyenv activate demo
```

