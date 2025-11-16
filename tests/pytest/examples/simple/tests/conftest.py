"""Общие фикстуры для тестов"""
import pytest


@pytest.fixture
def sample_data():
    """Фикстура с простыми тестовыми данными"""
    return {"x": 10, "y": 20}


@pytest.fixture
def user_data():
    """Фикстура с данными пользователя"""
    return {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com"
    }


@pytest.fixture
def numbers_list():
    """Фикстура со списком чисел"""
    return [1, 2, 3, 4, 5]


@pytest.fixture(scope="module")
def database_connection():
    """
    Фикстура с scope='module' - создается один раз для модуля
    Имитирует подключение к базе данных
    """
    print("\n[SETUP] Подключение к базе данных")
    connection = {"status": "connected", "db": "test_db"}
    yield connection
    print("\n[TEARDOWN] Отключение от базы данных")


@pytest.fixture(scope="session")
def config():
    """
    Фикстура с scope='session' - создается один раз для всех тестов
    Используется для дорогих операций
    """
    print("\n[SETUP] Загрузка конфигурации")
    return {
        "api_url": "https://api.example.com",
        "timeout": 30,
        "max_retries": 3
    }


@pytest.fixture
def temp_file(tmp_path):
    """
    Фикстура с использованием встроенной фикстуры tmp_path
    Создает временный файл для тестов
    """
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Тестовые данные")
    return file_path
