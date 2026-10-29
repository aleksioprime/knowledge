from fastapi import status
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import Receipt


def test_create_receipt(test_client):
    """
    Проверяет создание чека через POST-запрос.
    Используется тестовый клиент и тестовая база данных.
    """

    # Данные, которые должны быть отправлены в запросе
    data = {
        "total": 10000,
        "vat": 2000,
        "client_phone": "+79111111111",
        "cashier_inn": "7357735773577357",
    }

    # Отправляем POST /receipts/ и получаем ответ
    response = test_client.post("/receipts/", json=data)
    # Преобразуем тело ответа в dict
    data = response.json()

    # Проверяем корректный статус-код
    assert response.status_code == status.HTTP_201_CREATED
    # Проверяем, что сервер действительно создал объект (есть id)
    assert data["id"] is not None


def test_read_receipts(test_session: Session, test_client: TestClient):
    """
    Проверяет работу эндпоинта GET /receipts/.
    Тест:
        1. Создаёт две записи Receipt напрямую в тестовой базе.
        2. Отправляет запрос к эндпоинту.
        3. Проверяет, что вернулись все созданные записи.
    """

    # Создаём две записи прямо в базе данных (минуя API),
    # чтобы потом убедиться, что эндпоинт корректно возвращает сохранённые значения.
    receipt_1 = Receipt(
        total=10000,
        vat=2000,
        client_phone="+79111111111",
        cashier_inn="7357735773577357"
    )

    receipt_2 = Receipt(
        total=5000,
        vat=100,
        client_phone="+7953535353",
        cashier_inn="1111111111111111"
    )

    # Добавляем записи в сессию и фиксируем изменения в базе
    test_session.add(receipt_1)
    test_session.add(receipt_2)
    test_session.commit()

    # Выполняем GET-запрос к эндпоинту получения всех чеков
    response = test_client.get("/receipts/")

    # Преобразуем JSON-ответ в Python-структуру (список словарей)
    data = response.json()

    # Проверяем корректный статус-код
    assert response.status_code == status.HTTP_200_OK

    # Проверяем, что возвращено ровно 2 объекта
    assert len(data) == 2

    # Сравниваем значения, возвращённые API, с теми,
    # которые мы вручную вставили в тестовую базу
    for receipt, observed in zip((receipt_1, receipt_2), data):
        assert observed["id"] == receipt.id           # ID должен совпадать
        assert observed["total"] == receipt.total     # total должен совпадать
