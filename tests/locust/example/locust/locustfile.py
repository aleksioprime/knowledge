"""
Файл конфигурации Locust для нагрузочного тестирования FastAPI приложения.
Определяет поведение виртуальных пользователей и тестовые задачи.
"""

from locust import HttpUser, task, between


class WebsiteUser(HttpUser):
    """
    Класс виртуального пользователя для симуляции нагрузки на API
    """
    wait_time = between(1, 3)

    def on_start(self):
        """
        Метод выполняется один раз при запуске каждого пользователя.
        Выполняет авторизацию и сохраняет токен для последующих запросов.
        """
        # Выполняем авторизацию
        r = self.client.post(
            "/api/auth/login",
            data={"username": "user1", "password": "password"},
        )
        # Получаем токен из ответа
        token = r.json()["access_token"]
        # Добавляем токен в заголовки для всех последующих запросов
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task
    def profile(self):
        """
        Задача: получить профиль текущего пользователя.
        Выполняется с весом 1 (стандартный)
        """
        self.client.get("/api/profile")

    @task(2)
    def items(self):
        """
        Задача: получить список элементов.
        Выполняется с весом 2 (в 2 раза чаще чем другие задачи с весом 1)
        """
        self.client.get("/api/items")

    @task
    def create_item(self):
        """
        Задача: создать новый элемент.
        Выполняется с весом 1 (стандартный)
        """
        self.client.post("/api/items", json={"name": "Test", "price": 100})
