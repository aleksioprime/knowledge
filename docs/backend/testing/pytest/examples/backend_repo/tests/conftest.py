import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app, Base, get_session, get_repository, ReceiptCreate, ReceiptPublic


class FakeRepo:
    """
    Фейковый репозиторий, хранящий данные в обычном Python-списке.
    Используется для быстрых юнит-тестов бизнес-логики
    без поднятия реальной базы данных.
    """

    def __init__(self):
        # "База данных" — обычный список объектов ReceiptPublic
        self.data = []

    def create(self, data: ReceiptCreate) -> ReceiptPublic:
        """
        Имитация создания записи.
        - Генерирует id по длине списка.
        - Преобразует ReceiptCreate → ReceiptPublic
        - Сохраняет запись в список
        """
        new_record = ReceiptPublic(
            id=len(self.data) + 1,      # простой автоинкремент
            **data.model_dump()         # распаковка полей из pydantic-модели
        )
        self.data.append(new_record)
        return new_record

    def get_all(self, offset: int = 0, limit: int = 100) -> list[ReceiptPublic]:
        """
        Возвращает все записи из списка по принципу пагинации.
        """
        return self.data[offset:offset+limit]


@pytest.fixture()
def test_engine():
    """
    Фикстура создаёт тестовый SQLAlchemy engine для SQLite
    и автоматически создаёт все таблицы, необходимые для тестов.

    После окончания каждого теста таблицы удаляются (drop_all).
    """
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    # Создаём все таблицы из моделей (Base = declarative_base())
    Base.metadata.create_all(engine)
    # Передаём engine тесту
    yield engine
    # После выполнения теста — удаляем таблицы
    Base.metadata.drop_all(engine)

@pytest.fixture
def test_session(test_engine):
    """
    Фикстура создаёт SQLAlchemy Session для работы с тестовой БД.

    Каждому тесту выдаётся своя собственная сессия, связанная с test_engine.
    """
    with Session(test_engine) as session:
        yield session

@pytest.fixture
def test_client(test_session):
    """
    Фикстура создаёт TestClient (тестовый HTTP клиент FastAPI),
    но главное — подменяет зависимость get_session так,
    чтобы в эндпоинты попадала именно тестовая Session.

    Это позволяет выполнять тесты без использования реальной базы.
    """
    # Подменяем зависимость get_session → используем тестовую сессию
    app.dependency_overrides[get_session] = lambda: test_session
    # Возвращаем тестовый клиент
    yield TestClient(app)
    # После теста — обязательно очищаем подмены зависимостей
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def fake_repo():
    """
    Фикстура возвращает экземпляр FakeRepo — фейкового репозитория.
    Он используется для тестов, где не нужна настоящая база данных,
    а вместо этого важно проверить логику слоя UoW / сервиса.
    """
    return FakeRepo()

@pytest.fixture
def test_client_with_fake_uow(fake_repo):
    """
    Фикстура создаёт TestClient, но подменяет зависимость get_repository
    на FakeRepo. Это позволяет протестировать API без настоящей БД,
    используя in-memory хранилище (список).

    Используется, если приложение построено по паттерну Repository + UoW.
    """
    app.dependency_overrides[get_repository] = lambda: fake_repo
    yield TestClient(app)
    # Чистим dependency_overrides, чтобы другие тесты не сломались
    app.dependency_overrides.clear()