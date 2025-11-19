"""
Фикстуры для работы с авторизацией и пользователями в тестах.
"""
import pytest
from httpx import Response

from testdata import test_data_loader


@pytest.fixture()
def test_user_data():
    """Возвращает данные обычного тестового пользователя"""
    return test_data_loader.get_regular_user()


@pytest.fixture()
def admin_user_data():
    """Возвращает данные админ-пользователя"""
    return test_data_loader.get_admin_user()


@pytest.fixture()
def all_users_data():
    """Возвращает список всех тестовых пользователей"""
    return test_data_loader.get_users()


@pytest.fixture()
async def create_test_user(make_post_request, test_user_data):
    """
    Создает тестового пользователя в системе.
    Примечание: требует наличие эндпоинта для регистрации или прямого создания в БД
    """
    # TODO: Реализовать создание пользователя через API или напрямую в БД
    # Пока предполагаем, что пользователь уже создан через миграции/seed
    return test_user_data


@pytest.fixture()
async def auth_tokens(make_post_request, test_user_data) -> dict:
    """
    Выполняет авторизацию и возвращает токены (access и refresh).
    """
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }

    response: Response = await make_post_request("/api/login/", json=login_data)
    assert response.status_code == 200, f"Ошибка авторизации: {response.text}"

    tokens = response.json()
    return tokens


@pytest.fixture()
async def admin_auth_tokens(make_post_request, admin_user_data) -> dict:
    """
    Выполняет авторизацию админа и возвращает токены.
    """
    login_data = {
        "username": admin_user_data["username"],
        "password": admin_user_data["password"]
    }

    response: Response = await make_post_request("/api/login/", json=login_data)
    assert response.status_code == 200, f"Ошибка авторизации админа: {response.text}"

    tokens = response.json()
    return tokens


@pytest.fixture()
async def auth_headers(auth_tokens) -> dict:
    """
    Возвращает заголовки с access токеном для авторизованных запросов.
    """
    return {
        "Authorization": f"Bearer {auth_tokens['access_token']}"
    }


@pytest.fixture()
async def admin_auth_headers(admin_auth_tokens) -> dict:
    """
    Возвращает заголовки с access токеном админа для авторизованных запросов.
    """
    return {
        "Authorization": f"Bearer {admin_auth_tokens['access_token']}"
    }
