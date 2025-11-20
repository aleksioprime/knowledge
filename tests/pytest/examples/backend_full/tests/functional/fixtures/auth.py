"""
Фикстуры для работы с авторизацией в тестах.
"""
import random
import pytest
from httpx import Response

from testdata.loader import load_test_data


@pytest.fixture()
def test_user_data():
    """Возвращает данные случайного обычного тестового пользователя"""
    users = load_test_data('users.json')['users']
    non_admin_users = [user for user in users if not user.get('is_admin', False)]
    return random.choice(non_admin_users)


@pytest.fixture()
async def auth_tokens(make_post_request, test_user_data) -> dict:
    """Выполняет авторизацию и возвращает токены (access и refresh)"""
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response: Response = await make_post_request("/api/login/", json=login_data)
    assert response.status_code == 200, f"Ошибка авторизации: {response.text}"
    return response.json()


@pytest.fixture()
def admin_user_data():
    """Возвращает данные случайного админ-пользователя"""
    users = load_test_data('users.json')['users']
    admin_users = [user for user in users if user.get('is_admin', False)]
    return random.choice(admin_users)


@pytest.fixture()
async def admin_auth_tokens(make_post_request, admin_user_data) -> dict:
    """Выполняет авторизацию админа и возвращает токены"""
    login_data = {
        "username": admin_user_data["username"],
        "password": admin_user_data["password"]
    }
    response: Response = await make_post_request("/api/login/", json=login_data)
    assert response.status_code == 200, f"Ошибка авторизации админа: {response.text}"
    return response.json()


@pytest.fixture()
async def auth_headers(auth_tokens) -> dict:
    """Возвращает заголовки с access токеном для авторизованных запросов"""
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}


@pytest.fixture()
async def admin_auth_headers(admin_auth_tokens) -> dict:
    """Возвращает заголовки с access токеном админа для авторизованных запросов"""
    return {"Authorization": f"Bearer {admin_auth_tokens['access_token']}"}
