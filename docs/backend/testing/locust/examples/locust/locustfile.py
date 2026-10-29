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
        # Список для отслеживания созданных items
        self.created_items = []

        # Выполняем авторизацию
        r = self.client.post(
            "/api/auth/login",
            data={"username": "user_test", "password": "password"},
        )
        # Получаем токен из ответа
        token = r.json()["access_token"]
        # Добавляем токен в заголовки для всех последующих запросов
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    def on_stop(self):
        """
        Метод выполняется один раз при остановке каждого пользователя.
        Удаляет все созданные items с помощью массового удаления.
        """
        # Удаляем созданные items
        if self.created_items:
            try:
                response = self.client.post(
                    "/api/items/delete-batch",
                    json={"item_ids": self.created_items}
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"Batch delete: {result['deleted']} items deleted, {result['not_found']} not found")
            except Exception as e:
                print(f"Failed to batch delete items: {e}")

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
        response = self.client.post("/api/items", json={"name": "Test", "price": 100})
        if response.status_code == 200:
            # Сохраняем ID созданного item для последующего удаления
            item_data = response.json()
            self.created_items.append(item_data["id"])

    @task
    def delete_item(self):
        """
        Задача: удалить случайный элемент из созданных.
        Выполняется с весом 1 (стандартный)
        """
        if self.created_items:
            # Удаляем последний созданный item
            item_id = self.created_items.pop()
            self.client.delete(f"/api/items/{item_id}")

    @task
    def update_item(self):
        """
        Задача: обновить случайный элемент из созданных.
        Выполняется с весом 1 (стандартный)
        """
        if self.created_items:
            # Обновляем случайный item (последний в списке)
            item_id = self.created_items[-1]
            # Обновляем только цену
            self.client.put(
                f"/api/items/{item_id}",
                json={"price": 200.50}
            )
