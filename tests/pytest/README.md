# Тестирование с помощью pytest

### Установка PyTest

Установка pytest с помощью pip
```sh
pip install pytest
```

Проверка версии:
```sh
pytest --version
```

### Структура проекта и поиск тестов

Pytest автоматически ищет:
- файлы: test_*.py или *_test.py
- функции: def test_*
- классы: class TestSomething: (без __init__!)

Пример простой структуры:
```
project/
│── app/
│   ├── main.py
│   └── utils.py
│── tests/
│   ├── test_main.py
│   ├── test_utils.py
│   └── conftest.py
```

### Конфигурация

Конфигурация в `pytest.ini`
```
[pytest]
;Где искать тесты
testpaths = tests
;Шаблон для поиска тестов
python_files = "test_*.py"
; Дополнительные опции (-v — подробный вывод)
; Применение флагов командной строки
addopts = -v
```

Конфигурация в `pyproject.toml`
```
[tool.pytest.ini_options]
addopts = "-v"
python_files = "test_*.py"
testpaths = "tests"
```

### Простой тест

```python
def test_add():
    assert 1 + 1 == 2, "Сложение выполнено неправильно"
```

### Запуск тестов
```sh
pytest                          # Запустит все тесты
pytest -k "test_read_receipts"  # Запустит только этот тест
pytest -k "TestReceipts"        # Запустит все тесты внутри класса TestReceipts
pytest -k "read"                # Запустит все тесты, где есть 'read' в названии
```

### Ассерты
```python
# Числа
assert 1 == 1
assert 1 != 2
assert 5 < 10

# Строки
assert "test" == "test"
assert "test" in "this is a test string"
assert "test str".startswith("t")

# Списки
numbers = [1, 2, 3, 4, 5]
assert len(numbers) == 5
assert 3 in numbers

# Объекты и классы
class User:
    def __init__(self, name):
        self.name = name

user = User("Anton")
assert user.name == "Anton"
assert isinstance(user, User)
assert hasattr(user, 'name')
```

### Проверка ошибок

```python
def test_error():
    with pytest.raises(ValueError):
        int("hello")
```

```python
with pytest.raises(ValueError, match="invalid literal"):
    int("hello")
```

### Группировка тестов

```python
class TestMath:
    def test_add(self):
        assert 1 + 1 == 2

    def test_sub(self):
        assert 5 - 3 == 2

    def test_mul(self):
        assert 3 * 4 == 12
```

Преимущества групппировки:
- Тесты, связанные одной функциональностью, находятся в одном классе (проще находить и поддерживать тесты для конкретного модуля или фичи)
- Общие фикстуры только для тестов класса
- Применение маркеров на уровне класса

### Паттерн ААА(три А)

Структура юнит теста:
- arrange(подготовка): Подготовка тестовых данных
- act(действие): Выполнение тестового кода
- assert(проверка): Проверка результатов

```python
class TestFindElemIndex:
    """Тесты функции find_elem_index с применением AAA подхода"""
    TEST_TEXT = "abcdef"

    def test_find_existing_element(self):
        """Нахождение существующего элемента"""
        # Arrange
        search_element = "c"
        expected_index = 2

        # Act
        result = find_elem_index(self.TEST_TEXT, search_element)

        # Assert
        assert result == expected_index
```

### Параметризация

```python
import pytest

@pytest.mark.parametrize("x,y,res", [
    (1, 2, 3),
    (10, 5, 15),
    (-1, 1, 0)
])
def test_add(x, y, res):
    assert x + y == res
```

### Методология TDD
Test-Driven Development (TDD) — это методология разработки, при которой код пишется после написания тестов.

Цикл TDD (Красный → Зелёный → Рефакторинг):
- Красный — Пишем падающий тест на новую функциональность.
- Зелёный — Пишем минимальный код, чтобы тест прошёл.
- Рефакторинг — Улучшаем код, сохраняя работоспособность.


### Фикстуры

Фикстуры - это вспомогательные функции, которые позволяют:
- подготавливать данные
- открывать соединения
- запускать временные базы
- передавать зависимости

Пример фикстуры:
```python
import pytest

@pytest.fixture
def sample():
    return {"x": 10, "y": 20}
```

Использование:
```python
def test_sum(sample):
    assert sample["x"] + sample["y"] == 30
```

### Области видимости (scope) фикстур

- function (по умолчанию) — новая фикстура для каждого теста.
- class — одна фикстура на весь класс тестов.
- module — одна фикстура на модуль (файл с тестами).
- package — одна фикстура на пакет (директорию с тестами).
- session — одна фикстура на все тесты в запуске.

Порядок скоупов: session → package → module → class → function

- session - дорогие ресурсы (БД, API-клиенты) (db_connection, config)
- module - общие данные для всех тестов в файле (test_data, mock_service)
- class - общие зависимости для методов класса (api_client, auth_header)
- function - изолированные данные для каждого теста (clean_db, temp_file)

### Использование conftest.py

Файл, содержащий общие фикстуры для директории, используется для:
- Упрощение тестов: фикстуры из conftest.py автоматически доступны во всех тестах без явного импорта
- Переиспользование кода: общие настройки (например, подключение к БД, создание тестовых данных) можно вынести в conftest.py и использовать в разных тестах
- Гибкость: можно переопределять фикстуры для конкретных тестов или папок, поддерживает область видимости (scope="session", scope="module", scope="function")

```python
import pytest

@pytest.fixture
def db_conn():
    return "connection"
```

```python
def test_db(db_conn):
    assert db_conn == "connection"
```

### Маркировки
Маркировки отмечают тесты специальными характеристиками

Пример:
```python
@pytest.mark.slow
def test_x():
    ...
```
```sh
# Запуск только slow-тестов
pytest -m slow
```

Пропуск тестов:
```python
@pytest.mark.skip(reason="Not implemented")
def test_old():
    ...
```

Условный пропуск:
```python
@pytest.mark.skipif(sys.platform == "win32", reason="No Windows support")
def test_linux():
    ...
```

Ожидаемый провал:
```python
@pytest.mark.xfail
def test_fail():
    assert False
```

### Тестовые двойники

- Стабы (Stubs) - простые заглушки, возвращающие предопределенные данные (когда нужно просто проигнорировать внешний вызов - например, функция, которая всегда возвращает успешный ответ)
- Фейки (Fakes) - упрощенные, но рабочие реализации (когда нужно имитировать реальное поведение без сложностей - наример: in-memory база данных вместо реальной)
- Моки (Mocks) - объекты с предопределенными ожиданиями (когда важно проверить взаимодействие - например, проверка, что был вызван метод post с определенными параметрами)

```python
# Пример стаба
def get_user_from_db_stub(user_id):
    return {"id": user_id, "name": "Test User"}

# Использование
def test_greeting(monkeypatch):

    def stub(user_id):
        return {"id": user_id, "name": "Alice"}

    monkeypatch.setattr("app.services.get_user", stub)

    from app.main import greeting
    assert greeting(1) == "Hello, Alice!"
```

```python
# Пример фейковой базы
class FakeUserRepository:
    def __init__(self):
        self.users = {}

    def add(self, user):
        self.users[user["id"]] = user

    def get(self, user_id):
        return self.users.get(user_id)

# Использование
def test_user_repo():
    repo = FakeUserRepository()
    repo.add({"id": 1, "name": "Bob"})

    assert repo.get(1)["name"] == "Bob"
```

```python
# Пример использования мока
from unittest.mock import MagicMock

def test_payment():
    payment_service = MagicMock()
    payment_service.pay.return_value = True

    result = payment_service.pay(100)

    assert result is True
    payment_service.pay.assert_called_once_with(100)
```

### Покрытие

pytest-cov - это плагин для pytest, который позволяет измерять покрытие кода тестами (code coverage). Он интегрируется с инструментом coverage.py и предоставляет удобный способ проверки, какая часть вашего кода выполняется тестами.

```sh
# Установка плагина
pip install pytest-cov

# Запуск с измерением покрытия
pytest --cov=app
```

Можно включить в `pytest.init`
```
; Дополнительные опции (-v — подробный вывод)
addopts = -v --cov=app
```

Пример содержимого `.coveragerc`
```
[run]
branch = True

# Regexes для пропуска файлов и директорий
omit =
    */migrations/*
    */settings.py

[report]
# Падение при недостаточном покрытии
fail_under = 50
# Пропуск в отчете файлов со 100% покрытием
skip_covered = True
```

Пример конфигурирования `pyproject.toml`:
```
[tool.pytest.ini_options]
addopts = "-v --cov=src --cov-config=.coveragerc"
python_files = "test*.py"
testpaths = "src"

[tool.coverage.run]
branch = true
omit = [
    "*/__init__.py",
    "*/migrations/*",
    "*/settings.py",
]

[tool.coverage.report]
fail_under = 50
skip_covered = true
```

Дополнительные настройки:
- --cov-config=.coveragerc (использовать настройки из файла `.coveragerc`)
- --cov-report=term-missing (специально подсвечивает строки кода, не выполненные во время тестов)