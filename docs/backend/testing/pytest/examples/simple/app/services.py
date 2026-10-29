"""Модуль с функциями для демонстрации тестовых двойников"""


def get_user_from_db(user_id: int) -> dict:
    """
    Получает данные пользователя из базы данных
    (В реальном приложении здесь был бы запрос к БД)
    """
    # Имитация запроса к БД
    raise NotImplementedError("Подключение к БД не настроено")


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Отправляет email
    (В реальном приложении здесь была бы интеграция с SMTP)
    """
    # Имитация отправки email
    raise NotImplementedError("SMTP не настроен")


def greeting(user_id: int) -> str:
    """Возвращает приветствие для пользователя"""
    user = get_user_from_db(user_id)
    return f"Привет, {user['name']}!"


def process_payment(amount: float, payment_service) -> dict:
    """Обрабатывает платеж через внешний сервис"""
    result = payment_service.pay(amount)
    return {"success": result, "amount": amount}


class UserRepository:
    """Репозиторий для работы с пользователями"""

    def __init__(self):
        self.users = {}

    def add(self, user: dict) -> None:
        """Добавляет пользователя"""
        self.users[user["id"]] = user

    def get(self, user_id: int) -> dict | None:
        """Получает пользователя по ID"""
        return self.users.get(user_id)

    def delete(self, user_id: int) -> bool:
        """Удаляет пользователя"""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False


class ApiClient:
    """Клиент для работы с API"""

    def fetch_data(self, endpoint: str) -> dict:
        """Получает данные из API"""
        raise NotImplementedError("API не доступен")
