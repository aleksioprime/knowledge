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
    assert 1 + 1 == 2
```

### Запуск тестов

```sh
pytest                          # Все тесты
pytest tests/test_app.py        # Конкретный файл
pytest tests/                   # Все тесты в директории
pytest -v                       # Подробный вывод
pytest -s                       # Показать print
pytest -x                       # Остановиться на первой ошибке
pytest -k "test_user"           # Только тесты с "test_user" в названии
pytest -m slow                  # Только тесты с маркировкой @pytest.mark.slow
pytest --lf                     # Запустить только упавшие тесты
pytest --ff                     # Сначала упавшие, потом остальные
```

### Ассерты

```python
# Равенство
assert 1 == 1
assert "hello" == "hello"

# Неравенство
assert 1 != 2

# Сравнения
assert 5 > 3
assert 2 < 10
assert 5 >= 5

# Принадлежность
assert "a" in "abc"
assert 3 in [1, 2, 3]
assert "key" in {"key": "value"}

# Строки
assert "test".startswith("t")
assert "hello".endswith("o")

# Булевы значения
assert True
assert not False

# None
assert value is None
assert value is not None

# Типы
assert isinstance(5, int)
assert isinstance("text", str)

# Атрибуты
assert hasattr(obj, "name")
```

### Проверка ошибок

```python
def test_error():
    with pytest.raises(ValueError):
        int("hello")
```

### Проверка исключений

```python
import pytest

def test_error():
    with pytest.raises(ValueError):
        int("hello")

def test_error_message():
    with pytest.raises(ValueError, match="invalid literal"):
        int("hello")

def test_zero_division():
    with pytest.raises(ZeroDivisionError):
        1 / 0
```

### Группировка тестов

```python
class TestMath:
    def test_add(self):
        assert 1 + 1 == 2

    def test_sub(self):
        assert 5 - 3 == 2
```

Преимущества групппировки:
- Тесты, связанные одной функциональностью, находятся в одном классе (проще находить и поддерживать тесты для конкретного модуля или фичи)
- Общие фикстуры только для тестов класса
- Применение маркеров на уровне класса

### Паттерн AAA (Arrange-Act-Assert)

Структура юнит теста:
- arrange(подготовка): Подготовка тестовых данных
- act(действие): Выполнение тестового кода
- assert(проверка): Проверка результатов

```python
def test_user_creation():
    # Arrange - подготовка данных
    name = "Alice"
    age = 30

    # Act - выполнение действия
    user = User(name, age)

    # Assert - проверка результата
    assert user.name == "Alice"
    assert user.age == 30
```

### Параметризация

```python
import pytest

@pytest.mark.parametrize("x, y, expected", [
    (1, 2, 3),
    (5, 5, 10),
    (-1, 1, 0),
])
def test_add(x, y, expected):
    assert x + y == expected
```

**Множественная параметризация:**
```python
@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [3, 4])
def test_multiply(x, y):
    assert x * y > 0  # Будет 4 теста: 1*3, 1*4, 2*3, 2*4
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
def user():
    return {"name": "Alice", "age": 30}

def test_user_name(user):
    assert user["name"] == "Alice"
```

**Фикстура с setup/teardown:**
```python
@pytest.fixture
def database():
    db = connect_db()  # Setup
    yield db           # Предоставление ресурса
    db.close()         # Teardown
```

### Области видимости (scope) фикстур

Порядок скоупов: session → package → module → class → function

- session - одна фикстура на все тесты в запуске, дорогие ресурсы (БД, API-клиенты) (db_connection, config)
- module - одна фикстура на модуль (файл с тестами), общие данные для всех тестов в файле (test_data, mock_service)
- class - одна фикстура на весь класс тестов, общие зависимости для методов класса (api_client, auth_header)
- function - новая фикстура для каждого теста, изолированные данные (clean_db, temp_file)

```python
@pytest.fixture(scope="function")  # По умолчанию - новая для каждого теста
def user():
    return User()

@pytest.fixture(scope="class")  # Одна на класс
def db_connection():
    return connect()

@pytest.fixture(scope="module")  # Одна на файл
def app_config():
    return load_config()

@pytest.fixture(scope="session")  # Одна на весь запуск
def database():
    return init_db()
```

### Файл conftest.py

Файл с общими фикстурами, доступными во всех тестах без импорта.

**conftest.py:**
```python
import pytest

@pytest.fixture
def api_client():
    return Client("http://api.example.com")
```

**test_api.py:**
```python
def test_get_users(api_client):  # Фикстура доступна автоматически
    response = api_client.get("/users")
    assert response.status == 200
```

**Расположение:**
- `tests/conftest.py` - фикстуры для всех тестов
- `tests/api/conftest.py` - только для тестов в `api/`

### Встроенные фикстуры

**tmp_path** - временная директория:
```python
def test_file(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("content")
    assert file.read_text() == "content"
```

**capsys** - захват stdout/stderr:
```python
def test_print(capsys):
    print("Hello")
    captured = capsys.readouterr()
    assert "Hello" in captured.out
```

**monkeypatch** - подмена объектов:
```python
def test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_key")
    assert os.getenv("API_KEY") == "test_key"
```

**request** - информация о тесте:
```python
@pytest.fixture
def setup(request):
    print(f"Running: {request.node.name}")
```

### Маркировки

Маркировки отмечают тесты специальными характеристиками

**Встроенные маркировки:**
```python
import pytest

@pytest.mark.skip(reason="Не реализовано")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.version_info < (3, 10), reason="Требуется Python 3.10+")
def test_new_syntax():
    pass

@pytest.mark.xfail(reason="Известный баг")
def test_known_issue():
    assert False
```

**Пользовательские маркировки:**
```python
@pytest.mark.slow
def test_long_operation():
    time.sleep(5)

@pytest.mark.integration
def test_api_call():
    pass
```

**Запуск:**
```sh
pytest -m slow                        # Только медленные тесты
pytest -m "not slow"                  # Все кроме медленных
pytest -m "slow and integration"      # С обеими маркировками
```

**Регистрация в pytest.ini:**
```ini
[pytest]
markers =
    slow: медленные тесты
    integration: интеграционные тесты
```

### Тестовые двойники

**Стабы (Stubs)** - заглушки с фиксированными данными:
```python
def test_greeting(monkeypatch):
    def stub_get_user(user_id):
        return {"name": "Alice"}

    monkeypatch.setattr("app.get_user", stub_get_user)
    assert greeting(1) == "Hello, Alice!"
```

**Фейки (Fakes)** - упрощенные рабочие реализации:
```python
class FakeDB:
    def __init__(self):
        self.data = {}

    def save(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

def test_db():
    db = FakeDB()
    db.save("user1", {"name": "Bob"})
    assert db.get("user1")["name"] == "Bob"
```

**Моки (Mocks)** - проверка взаимодействия:
```python
from unittest.mock import Mock, MagicMock

def test_api_call():
    api = Mock()
    api.get.return_value = {"status": "ok"}

    result = api.get("/users")

    assert result["status"] == "ok"
    api.get.assert_called_once_with("/users")
```

**Использование patch:**
```python
from unittest.mock import patch

@patch("requests.get")
def test_fetch_data(mock_get):
    mock_get.return_value.json.return_value = {"data": "test"}

    result = fetch_data()
    assert result["data"] == "test"
```

### Покрытие кода (Coverage)

```sh
# Установка
pip install pytest-cov

# Запуск с покрытием
pytest --cov=app                    # Базовый отчет
pytest --cov=app --cov-report=html  # HTML отчет
pytest --cov=app --cov-report=term-missing  # Показать пропущенные строки
```

**Конфигурация в pytest.ini:**
```ini
[pytest]
addopts = --cov=app --cov-report=term-missing
```

**Конфигурация в pyproject.toml:**
```toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-report=term-missing"

[tool.coverage.run]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 80
skip_covered = true
```
