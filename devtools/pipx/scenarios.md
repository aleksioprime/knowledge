# pipx — сценарии использования

Пошаговые рецепты по запуску CLI-утилит через pipx.
Все команды выполняются в обычном терминале.

## Проверка установки

```bash
pipx --version
pipx list
```

## Сценарий 1. Поставить базовый набор Python-разработчика

Это «джентльменский набор» — то, что нужно почти любому Python-разработчику.

```bash
pipx install poetry
pipx install ruff
pipx install mypy
pipx install pre-commit
pipx install black
pipx install httpie
```

```bash
pipx list
```

## Сценарий 2. Сгенерировать проект из шаблона

`cookiecutter` создаёт проекты по готовому шаблону. Не нужно держать его постоянно — используем `pipx run`.

```bash
# Шаблон Python-пакета
pipx run cookiecutter gh:audreyfeldroy/cookiecutter-pypackage

# Шаблон FastAPI-проекта
pipx run cookiecutter gh:arthurhenrique/cookiecutter-fastapi

# Можно прямо из локальной папки
pipx run cookiecutter ./my-template
```

## Сценарий 3. Разовый запуск без установки

`pipx run` качает и запускает утилиту во временном venv. Удобно для одноразовых задач.

```bash
# Отформатировать один файл и забыть
pipx run black --check --diff some_script.py

# Сгенерировать pyinstaller-сборку
pipx run pyinstaller --onefile my_script.py
```

## Сценарий 4. Установка с extras и зависимостями

```bash
# Установить httpie со всеми extras
pipx install 'httpie[all]'

# Установить пакет с дополнительными CLI-командами в PATH
pipx install --include-deps ansible

# Доустановить плагин в venv установленной утилиты
pipx inject mkdocs mkdocs-material mkdocs-mermaid2-plugin
```

## Сценарий 5. Обслуживание установленных утилит

```bash
pipx upgrade-all       # обновить все
pipx upgrade poetry    # обновить одну
pipx reinstall-all     # переустановить после смены Python
pipx uninstall black   # удалить
```

## Сценарий 6. Поставить утилиту из Git

Полезно, когда нужна ветка/форк или утилита ещё не в PyPI.

```bash
pipx install git+https://github.com/user/repo.git
pipx install git+https://github.com/user/repo.git@dev-branch
pipx install 'git+https://github.com/user/repo.git#egg=pkg[extra]'
```

## Сценарий 7. Запустить конкретный entry-point из пакета

Иногда пакет называется одним именем, а CLI — другим. Например пакет `babel` поставляет команду `pybabel`.

```bash
pipx run --spec babel pybabel --help
pipx run --spec chardet chardetect myfile.txt
```

## Где живут venv

```bash
pipx environment --value PIPX_LOCAL_VENVS   # где лежат venv утилит
ls "$(pipx environment --value PIPX_LOCAL_VENVS)"
```

## Связанные темы

- [pipx](README.md)
- [uv: сценарии](../uv/scenarios.md)
- [Линтеры: сценарии](../linter/scenarios.md)
