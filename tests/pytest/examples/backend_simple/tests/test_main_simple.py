from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app, get_session, Base


def test_create_receipt():
        # Создаём тестовый SQLite-движок.
        # "check_same_thread=False" позволяет выполнять запросы из разных потоков
        # TestClient работает параллельно
        engine = create_engine(
            "sqlite:///testing.db", connect_args={"check_same_thread": False}
        )

        # Создаём все таблицы в тестовой базе данных
        Base.metadata.create_all(engine)

        # Создаём новую сессию для работы с БД:
        with Session(engine) as session:
            # Определяем функцию, которая будет подставляться вместо реальной зависимости get_session
            def get_session_override():
                return session

            # Регистрируем подмену зависимости
            # Любой эндпоинт, который использует Depends(get_session), теперь будет получать тестовую сессию
            app.dependency_overrides[get_session] = get_session_override

            # Создаём тестовый клиент FastAPI
            # Он позволяет отправлять запросы к приложению как будто это настоящий HTTP-сервер
            test_client = TestClient(app)

            # Данные, которые отправятся в POST-запросе
            data = {
                "total": 10000,
                "vat": 2000,
                "client_phone": "+79111111111",
                "cashier_inn": "7357735773577357",
            }

            # Отправляем POST-запрос на создание чека
            response = test_client.post("/receipts/", json=data)
            # После теста нужно очистить зависимость, чтобы последующие тесты не получили подмену
            app.dependency_overrides.clear()
            # Получаем JSON-ответ
            data = response.json()

        # Проверяем, что эндпоинт вернул именно статус 201 CREATED
        assert response.status_code == status.HTTP_201_CREATED
        # Проверяем, что сервер создал запись и вернул ID
        assert data["id"] is not None
