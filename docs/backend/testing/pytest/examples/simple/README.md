# Простые примеры pytest

Этот проект содержит простые примеры для изучения pytest.

## Структура проекта

```
.
├── app/                          # Код приложения
│   ├── example.py               # Простые функции для поиска элементов
│   ├── extention_example.py     # Расширенные версии с проверками
│   ├── math_operations.py       # Математические операции
│   └── services.py              # Сервисы для демонстрации мокирования
├── tests/                        # Тесты
│   ├── conftest.py              # Общие фикстуры
│   ├── test_simple.py           # Базовые примеры тестов
│   ├── test_simple_aaa.py       # Примеры AAA-паттерна
│   ├── test_simple_parameters.py # Параметризация тестов
│   ├── test_group_simple.py     # Группировка тестов в классы
│   ├── test_math_operations.py  # Тесты математических операций
│   ├── test_fixtures.py         # Примеры работы с фикстурами
│   ├── test_markers.py          # Примеры маркировок
│   └── test_doubles.py          # Тестовые двойники (stubs, fakes, mocks)
└── pytest.ini                    # Конфигурация pytest
```

## Что демонстрируют примеры

### 1. Базовые концепции

**test_simple.py** - Простейшие тесты
- Базовые assert-утверждения
- Проверка исключений с `pytest.raises`
- Проверка типов данных

### 2. Паттерн AAA (Arrange-Act-Assert)

**test_simple_aaa.py** - Структура юнит-тестов
- Arrange: Подготовка тестовых данных
- Act: Выполнение тестируемого кода
- Assert: Проверка результатов

### 3. Параметризация

**test_simple_parameters.py** - Параметризованные тесты
- `@pytest.mark.parametrize` для множественных входных данных
- Сокращение дублирования кода
- Матричная параметризация

**test_math_operations.py** - Комплексный пример
- Группировка тестов в классы
- Параметризация
- Проверка исключений

### 4. Группировка тестов

**test_group_simple.py** - Организация тестов в классы
- Объединение связанных тестов
- Общие константы для класса
- Чистая структура

### 5. Фикстуры

**conftest.py** - Общие фикстуры
- Фикстуры с разными scope (function, module, session)
- Setup и teardown
- Встроенные фикстуры (tmp_path)

**test_fixtures.py** - Использование фикстур
- Простые фикстуры
- Фикстуры с областями видимости
- Локальные и глобальные фикстуры
- Фикстуры с очисткой ресурсов

### 6. Маркировки

**test_markers.py** - Маркировка тестов
- `@pytest.mark.skip` - пропуск тестов
- `@pytest.mark.skipif` - условный пропуск
- `@pytest.mark.xfail` - ожидаемые провалы
- Пользовательские маркировки (slow, fast, integration, unit, database)
- Маркировка классов
- Маркировка параметров

### 7. Тестовые двойники

**test_doubles.py** - Stubs, Fakes, Mocks
- **Стабы (Stubs)**: простые заглушки с `monkeypatch`
- **Фейки (Fakes)**: упрощенные рабочие реализации
- **Моки (Mocks)**: проверка взаимодействия с `MagicMock`
- Использование `@patch`
- Проверка вызовов и аргументов

## Запуск тестов

### Все тесты
```bash
pytest
```

### Конкретный файл
```bash
pytest tests/test_math_operations.py
```

### С подробным выводом
```bash
pytest -v
```

### Только быстрые тесты
```bash
pytest -m fast
```

### Все, кроме медленных
```bash
pytest -m "not slow"
```

### Тесты по ключевому слову
```bash
pytest -k "math"
pytest -k "fixture"
pytest -k "TestMath"
```

### С выводом print
```bash
pytest -s
```

### Запуск конкретного теста
```bash
pytest tests/test_math_operations.py::TestMathOperations::test_add
pytest tests/test_fixtures.py::test_sample_data
```

### Показать доступные маркировки
```bash
pytest --markers
```

### Остановиться на первой ошибке
```bash
pytest -x
```

### Показать локальные переменные при ошибке
```bash
pytest -l
```

## Полезные комбинации

```bash
# Подробный вывод + показать print + остановиться на ошибке
pytest -vsx

# Запустить только интеграционные тесты с подробным выводом
pytest -v -m integration

# Запустить тесты с "math" в названии, исключая медленные
pytest -k "math" -m "not slow"

# Показать 10 самых медленных тестов
pytest --durations=10
```

## Результаты запуска

При успешном запуске вы должны увидеть:
- ✅ 70 тестов пройдено (PASSED)
- ⏭️  1 тест пропущен (SKIPPED)
- ⚠️  2 теста с ожидаемым провалом (XFAILED)

## Изучение кода

Рекомендуемый порядок изучения:

1. `test_simple.py` - начните с базовых тестов
2. `test_simple_aaa.py` - изучите AAA-паттерн
3. `test_group_simple.py` - группировка тестов
4. `test_simple_parameters.py` - параметризация
5. `test_math_operations.py` - комплексный пример
6. `conftest.py` и `test_fixtures.py` - фикстуры
7. `test_markers.py` - маркировки
8. `test_doubles.py` - продвинутое мокирование

Каждый файл содержит подробные комментарии и примеры использования.
