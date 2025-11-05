## Установка Poetry на Linux/MacOS

[Официальная инструкция](https://python-poetry.org/docs/#installation)

Установите Poetry из официального репозитория:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

## Установка Poetry на Windows

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```
## Проверка установки

Проверьте установку poetry:

```sh
poetry --version
```
## Создание проекта

```bash
poetry init
```

Или если уже есть папка с кодом, просто:

```bash
poetry install
```

_(Создаст и/или установит зависимости из pyproject.toml, если такой уже есть)_

---

## 3. **Задайте версию Python:**

```bash
poetry env use 3.12
```

_(Обязательно убедитесь, что Python 3.12 установлен!)_

---

## 4. **Добавьте зависимости:**

```bash
poetry add pandas
```

_(Или дополнительные, если используете LLM: openai и т.д.)_

---

## 5. **Запустите shell poetry:**

```bash
poetry shell
```

Теперь вы работаете в виртуальном окружении этого проекта.

---

## 6. **Запустите проект:**

```bash
python main.py
```

---

### **Пример полного цикла команд:**

```bash
cd project
poetry init         # Можно просто нажимать Enter на всех вопросах (или редактировать вручную pyproject.toml)
poetry env use 3.12
poetry add pandas
poetry shell
python main.py
```

---

### **pyproject.toml (пример):**

```toml
[tool.poetry]
name = "freelancer-earnings-cli"
version = "0.1.0"
description = "CLI анализатор доходов фрилансеров"
authors = ["Ваше Имя <your@email.com>"]

[tool.poetry.dependencies]
python = "^3.12"
pandas = "^2.2.2"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

_(Автоматически создается командой `poetry init`)_

---

**Теперь вы можете использовать Poetry shell и быть уверенным, что окружение — чистое, зависимости установлены, и ваш проект изолирован.**  
Если что-то не запускается — дайте сообщение об ошибке, помогу разобраться!