"""Примеры использования фикстур"""
import pytest


def test_sample_data(sample_data):
    """Использование простой фикстуры"""
    assert sample_data["x"] == 10
    assert sample_data["y"] == 20
    assert sample_data["x"] + sample_data["y"] == 30


def test_user_data(user_data):
    """Использование фикстуры с данными пользователя"""
    assert user_data["name"] == "Alice"
    assert user_data["email"] == "alice@example.com"
    assert isinstance(user_data["id"], int)


def test_numbers_list(numbers_list):
    """Использование фикстуры со списком"""
    assert len(numbers_list) == 5
    assert sum(numbers_list) == 15
    assert max(numbers_list) == 5


def test_database_connection(database_connection):
    """Использование фикстуры с scope='module'"""
    assert database_connection["status"] == "connected"
    assert database_connection["db"] == "test_db"


def test_database_query(database_connection):
    """Еще один тест с той же фикстурой database_connection"""
    # Фикстура с scope='module' не пересоздается
    assert database_connection["status"] == "connected"


def test_config(config):
    """Использование фикстуры с scope='session'"""
    assert config["api_url"] == "https://api.example.com"
    assert config["timeout"] == 30


def test_temp_file(temp_file):
    """Использование фикстуры с временным файлом"""
    assert temp_file.exists()
    assert temp_file.read_text() == "Тестовые данные"


class TestFixturesInClass:
    """Группа тестов с использованием фикстур"""

    def test_with_sample_data(self, sample_data):
        """Тест с фикстурой внутри класса"""
        result = sample_data["x"] * 2
        assert result == 20

    def test_with_user_data(self, user_data):
        """Еще один тест с фикстурой"""
        assert "@" in user_data["email"]


@pytest.fixture
def custom_fixture():
    """Локальная фикстура только для этого модуля"""
    return "custom_value"


def test_custom_fixture(custom_fixture):
    """Использование локальной фикстуры"""
    assert custom_fixture == "custom_value"


@pytest.fixture
def setup_teardown_fixture():
    """Фикстура с setup и teardown"""
    # Setup
    print("\nНастройка ресурса")
    resource = {"data": "initialized"}

    yield resource  # Предоставление ресурса тесту

    # Teardown
    print("\nОчистка ресурса")
    resource.clear()


def test_setup_teardown(setup_teardown_fixture):
    """Тест с фикстурой setup/teardown"""
    assert setup_teardown_fixture["data"] == "initialized"
