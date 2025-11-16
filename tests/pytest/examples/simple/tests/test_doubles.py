"""Примеры использования тестовых двойников (Stubs, Fakes, Mocks)"""
import pytest
from unittest.mock import MagicMock, Mock, patch
from app.services import (
    greeting,
    process_payment,
    UserRepository,
    ApiClient,
    send_email
)


# ==================== СТАБЫ (STUBS) ====================
# Стабы - простые заглушки, возвращающие предопределенные данные


def test_greeting_with_stub(monkeypatch):
    """Использование стаба с monkeypatch"""

    def stub_get_user(user_id):
        """Стаб возвращает фиксированные данные"""
        return {"id": user_id, "name": "Alice"}

    # Подменяем функцию стабом
    monkeypatch.setattr("app.services.get_user_from_db", stub_get_user)

    # Тестируем
    result = greeting(1)
    assert result == "Привет, Alice!"


def test_greeting_different_user(monkeypatch):
    """Стаб для другого пользователя"""

    def stub_get_user(user_id):
        return {"id": user_id, "name": "Bob"}

    monkeypatch.setattr("app.services.get_user_from_db", stub_get_user)

    result = greeting(2)
    assert result == "Привет, Bob!"


# ==================== ФЕЙКИ (FAKES) ====================
# Фейки - упрощенные, но рабочие реализации


class FakeUserRepository:
    """Фейковый репозиторий - упрощенная рабочая версия"""

    def __init__(self):
        self.users = {}

    def add(self, user):
        self.users[user["id"]] = user

    def get(self, user_id):
        return self.users.get(user_id)

    def delete(self, user_id):
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False


def test_fake_repository():
    """Использование фейкового репозитория"""
    repo = FakeUserRepository()

    # Добавление пользователя
    user = {"id": 1, "name": "Alice"}
    repo.add(user)

    # Получение пользователя
    retrieved = repo.get(1)
    assert retrieved["name"] == "Alice"

    # Удаление пользователя
    assert repo.delete(1) is True
    assert repo.get(1) is None


def test_fake_repository_multiple_users():
    """Фейк с несколькими пользователями"""
    repo = FakeUserRepository()

    repo.add({"id": 1, "name": "Alice"})
    repo.add({"id": 2, "name": "Bob"})

    assert len(repo.users) == 2
    assert repo.get(1)["name"] == "Alice"
    assert repo.get(2)["name"] == "Bob"


class FakeApiClient:
    """Фейковый API клиент"""

    def __init__(self):
        self.data = {
            "/users/1": {"id": 1, "name": "Alice"},
            "/users/2": {"id": 2, "name": "Bob"},
        }

    def fetch_data(self, endpoint):
        return self.data.get(endpoint, {})


def test_fake_api_client():
    """Использование фейкового API клиента"""
    client = FakeApiClient()

    data = client.fetch_data("/users/1")
    assert data["name"] == "Alice"

    data = client.fetch_data("/users/2")
    assert data["name"] == "Bob"


# ==================== МОКИ (MOCKS) ====================
# Моки - объекты с предопределенными ожиданиями и проверкой взаимодействия


def test_payment_with_mock():
    """Использование мока для проверки взаимодействия"""
    # Создаем мок сервиса платежей
    payment_service = MagicMock()
    payment_service.pay.return_value = True

    # Тестируем функцию
    result = process_payment(100, payment_service)

    # Проверяем результат
    assert result["success"] is True
    assert result["amount"] == 100

    # Проверяем, что метод pay был вызван с правильными параметрами
    payment_service.pay.assert_called_once_with(100)


def test_payment_failed():
    """Тест с неуспешным платежом"""
    payment_service = MagicMock()
    payment_service.pay.return_value = False

    result = process_payment(50, payment_service)

    assert result["success"] is False
    payment_service.pay.assert_called_once_with(50)


def test_mock_with_side_effect():
    """Мок с побочным эффектом (исключением)"""
    payment_service = MagicMock()
    payment_service.pay.side_effect = Exception("Сервис недоступен")

    with pytest.raises(Exception) as exc_info:
        process_payment(100, payment_service)

    assert "Сервис недоступен" in str(exc_info.value)


def test_email_sending_with_mock(monkeypatch):
    """Мок для отправки email"""
    # Создаем мок
    mock_send_email = Mock(return_value=True)
    monkeypatch.setattr("app.services.send_email", mock_send_email)

    # Используем мок
    from app.services import send_email
    result = send_email("test@example.com", "Тест", "Содержимое")

    # Проверяем
    assert result is True
    mock_send_email.assert_called_once_with("test@example.com", "Тест", "Содержимое")


def test_mock_call_count():
    """Проверка количества вызовов мока"""
    mock_service = MagicMock()

    # Вызываем несколько раз
    mock_service.method(1)
    mock_service.method(2)
    mock_service.method(3)

    # Проверяем количество вызовов
    assert mock_service.method.call_count == 3


def test_mock_with_multiple_return_values():
    """Мок с разными возвращаемыми значениями"""
    mock_service = MagicMock()
    mock_service.get_value.side_effect = [1, 2, 3]

    assert mock_service.get_value() == 1
    assert mock_service.get_value() == 2
    assert mock_service.get_value() == 3


# ==================== ИСПОЛЬЗОВАНИЕ PATCH ====================


@patch("app.services.get_user_from_db")
def test_greeting_with_patch(mock_get_user):
    """Использование декоратора @patch"""
    mock_get_user.return_value = {"id": 1, "name": "Charlie"}

    result = greeting(1)

    assert result == "Привет, Charlie!"
    mock_get_user.assert_called_once_with(1)


def test_api_client_with_patch():
    """Патч метода класса"""
    with patch.object(ApiClient, 'fetch_data') as mock_fetch:
        mock_fetch.return_value = {"status": "success"}

        client = ApiClient()
        result = client.fetch_data("/test")

        assert result["status"] == "success"
        mock_fetch.assert_called_once_with("/test")


# ==================== СРАВНЕНИЕ ПОДХОДОВ ====================


def test_comparison_stub():
    """Стаб - просто возвращает данные, без проверки взаимодействия"""
    def stub_func():
        return "stub_result"

    result = stub_func()
    assert result == "stub_result"


def test_comparison_fake():
    """Фейк - рабочая упрощенная реализация"""
    repo = UserRepository()  # Используем реальный класс как фейк
    repo.add({"id": 1, "name": "Test"})

    assert repo.get(1)["name"] == "Test"


def test_comparison_mock():
    """Мок - проверяет взаимодействие"""
    mock = MagicMock()
    mock.method.return_value = "mock_result"

    result = mock.method("arg")

    # Проверяем не только результат, но и взаимодействие
    assert result == "mock_result"
    mock.method.assert_called_once_with("arg")
