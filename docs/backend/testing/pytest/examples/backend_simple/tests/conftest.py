import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app, Base, get_session


@pytest.fixture()
def test_engine():
    """
    Создаёт тестовый SQLAlchemy-движок для SQLite и
    автоматически создаёт все таблицы перед тестом.

    После выполнения тестов — удаляет таблицы (drop_all).
    """
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    # Создаём таблицы для тестовой базы
    Base.metadata.create_all(engine)
    # Передаём engine тесту
    yield engine
    # После выполнения тестов удаляем таблицы
    Base.metadata.drop_all(engine)

@pytest.fixture
def test_session(test_engine):
    """
    Создаёт SQLAlchemy-сессию, связанную с тестовым движком.
    Каждому тесту выдаётся собственная сессия.
    """
    with Session(test_engine) as session:
        yield session

@pytest.fixture
def test_client(test_session):
    """
    Создаёт TestClient FastAPI и подменяет зависимость get_session,
    чтобы эндпоинты использовали ТОЛЬКО тестовую сессию.

    После теста — очищает dependency_overrides.
    """
    # Подменяем зависимость FastAPI → вместо реальной БД используем тестовую
    app.dependency_overrides[get_session] = lambda: test_session
    # Создаём тестовый HTTP-клиент
    yield TestClient(app)
    # Возвращаем зависимости на место, чтобы не ломать другие тесты
    app.dependency_overrides.clear()