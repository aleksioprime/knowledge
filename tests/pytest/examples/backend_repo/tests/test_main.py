from fastapi import status
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import Receipt, ReceiptPublic
from tests.conftest import FakeRepo


def test_create_receipt(test_client: TestClient):
    """
    Тестирует создание чека через реальный эндпоинт POST /receipts/
    и использование реальной тестовой базы (через test_client).
    """
    # Данные, которые отправим в запрос
    data = {
        "total": 10000,
        "vat": 2000,
        "client_phone": "+79111111111",
        "cashier_inn": "7357735773577357",
    }

    # Отправляем POST-запрос к API
    response = test_client.post("/receipts/", json=data)
    # JSON-ответ сервера преобразуем в словарь
    data = response.json()

    # Проверяем статус-код 201 CREATED
    assert response.status_code == status.HTTP_201_CREATED
    # Проверяем, что в ответе есть id — значит чек был успешно создан
    assert data["id"] is not None

def test_read_receipts(test_session: Session, test_client: TestClient):
    """
    Тестирует чтение чеков через GET /receipts/
    с использованием реальной SQLAlchemy-тестовой базы.
    """
    # Создаём две записи вручную в тестовой БД (минуя API)
    receipt_1 = Receipt(total=10000, vat=2000, client_phone="+79111111111", cashier_inn="7357735773577357")
    receipt_2 = Receipt(total=5000, vat=100, client_phone="+7953535353", cashier_inn="1111111111111111")
    # Добавляем и сохраняем их в базе данных
    test_session.add(receipt_1)
    test_session.add(receipt_2)
    test_session.commit()

    # Отправляем GET-запрос ко всем чекам
    response = test_client.get("/receipts/")
    data = response.json()

    # Проверяем, что запрос успешен
    assert response.status_code == status.HTTP_200_OK
    # API должно вернуть ровно две записи
    assert len(data) == 2
     # Проверяем, что API вернул те же данные, что и были в базе
    for receipt, observed in zip((receipt_1, receipt_2), data):
        assert observed["id"] == receipt.id
        assert observed["total"] == receipt.total

def test_create_fake(test_client_with_fake_uow: TestClient):
    """
    Тест создания чека через API, но уже НЕ с реальной базой данных,
    а с использованием FakeRepo — in-memory репозитория.

    Это быстрый юнит-тест "поверх" API, но без SQLAlchemy.
    """

    # Данные для создания чека
    data = {
        "total": 10000,
        "vat": 2000,
        "client_phone": "+79111111111",
        "cashier_inn": "7357735773577357",
    }

    # POST-запрос к API, но backend использует FakeRepo вместо БД
    response = test_client_with_fake_uow.post("/receipts/", json=data)
    data = response.json()

    # Эндпоинт должен вернуть статус 201
    assert response.status_code == status.HTTP_201_CREATED
    # FakeRepo создаёт автоинкремент id, значит он обязательно должен быть
    assert data["id"] is not None

def test_read_receipts_fake(fake_repo: FakeRepo, test_client_with_fake_uow: TestClient):
    """
    Тест чтения чеков на фейковом репозитории.
    Здесь мы вручную кладём объекты в FakeRepo.data
    и проверяем, что API корректно их возвращает.
    """
    # Наполняем FakeRepo заранее подготовленными моделями
    receipt_1 = ReceiptPublic(id=1, total=10000, vat=2000, client_phone="+79111111111", cashier_inn="7357735773577357")
    receipt_2 = ReceiptPublic(id=2, total=5000, vat=100, client_phone="+7953535353", cashier_inn="1111111111111111")
    fake_repo.data.extend([receipt_1, receipt_2])

    # Отправляем GET-запрос
    response = test_client_with_fake_uow.get("/receipts/")
    data = response.json()

    # Проверяем, что запрос успешен
    assert response.status_code == status.HTTP_200_OK
    # FakeRepo должен вернуть обе записи
    assert len(data) == 2
    # Проверяем, что данные вернулись корректно
    for receipt, observed in zip((receipt_1, receipt_2), data):
        assert observed["id"] == receipt.id
        assert observed["total"] == receipt.total