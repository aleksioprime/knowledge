"""
Функциональные тесты для эндпоинтов авторизации.
Проверяют login, logout, refresh токенов.
"""
import pytest
from httpx import AsyncClient, Response


class TestAuthLogin:
    """Тесты для эндпоинта логина (POST /api/login/)"""

    @pytest.mark.asyncio
    async def test_login_success(self, make_post_request, test_user_data):
        """
        Тест успешной авторизации пользователя.
        Проверяет, что возвращаются корректные access и refresh токены.
        """
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }

        response: Response = await make_post_request("/api/login/", json=login_data)

        # Проверка статуса ответа
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"

        # Проверка структуры ответа
        data = response.json()
        assert "access_token" in data, "Отсутствует access_token в ответе"
        assert "refresh_token" in data, "Отсутствует refresh_token в ответе"

        # Проверка, что токены не пустые
        assert len(data["access_token"]) > 0, "access_token пустой"
        assert len(data["refresh_token"]) > 0, "refresh_token пустой"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, make_post_request, test_user_data):
        """
        Тест авторизации с неправильным паролем.
        Должен вернуть ошибку 401 Unauthorized.
        """
        login_data = {
            "username": test_user_data["username"],
            "password": "WrongPassword123!"
        }

        response: Response = await make_post_request("/api/login/", json=login_data)

        # Проверка статуса ответа
        assert response.status_code == 401, f"Ожидался статус 401, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, make_post_request):
        """
        Тест авторизации с несуществующим пользователем.
        Должен вернуть ошибку 401 Unauthorized.
        """
        login_data = {
            "username": "nonexistent_user_12345",
            "password": "SomePassword123!"
        }

        response: Response = await make_post_request("/api/login/", json=login_data)

        # Проверка статуса ответа
        assert response.status_code == 401, f"Ожидался статус 401, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_login_missing_username(self, make_post_request):
        """
        Тест авторизации без указания username.
        Должен вернуть ошибку валидации 422.
        """
        login_data = {
            "password": "SomePassword123!"
        }

        response: Response = await make_post_request("/api/login/", json=login_data)

        # Проверка статуса ответа
        assert response.status_code == 422, f"Ожидался статус 422, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_login_missing_password(self, make_post_request, test_user_data):
        """
        Тест авторизации без указания password.
        Должен вернуть ошибку валидации 422.
        """
        login_data = {
            "username": test_user_data["username"]
        }

        response: Response = await make_post_request("/api/login/", json=login_data)

        # Проверка статуса ответа
        assert response.status_code == 422, f"Ожидался статус 422, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, make_post_request):
        """
        Тест авторизации с пустыми credentials.
        Должен вернуть ошибку валидации 422.
        """
        login_data = {
            "username": "",
            "password": ""
        }

        response: Response = await make_post_request("/api/login/", json=login_data)

        # Проверка статуса ответа
        assert response.status_code == 422, f"Ожидался статус 422, получен {response.status_code}"


class TestAuthRefresh:
    """Тесты для эндпоинта обновления токена (POST /api/refresh/)"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, make_post_request, auth_tokens):
        """
        Тест успешного обновления access токена с использованием refresh токена.
        Должен вернуть новый access токен.
        """

        refresh_data = {
            "refresh_token": auth_tokens["refresh_token"]
        }

        response: Response = await make_post_request("/api/refresh/", json=refresh_data)

        # Проверка статуса ответа
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"

        # Проверка структуры ответа
        data = response.json()
        assert "access_token" in data, "Отсутствует access_token в ответе"

        # Проверка, что новый токен отличается от старого
        assert data["access_token"] != auth_tokens["access_token"], "Новый access_token совпадает со старым"

        # Проверка, что токен не пустой
        assert len(data["access_token"]) > 0, "access_token пустой"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, make_post_request):
        """
        Тест обновления токена с невалидным refresh токеном.
        Должен вернуть ошибку 401 Unauthorized.
        """
        refresh_data = {
            "refresh_token": "invalid_refresh_token_12345"
        }

        response: Response = await make_post_request("/api/refresh/", json=refresh_data)

        # Проверка статуса ответа
        assert response.status_code == 401, f"Ожидался статус 401, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, make_post_request):
        """
        Тест обновления токена без передачи refresh_token.
        Должен вернуть ошибку валидации 422.
        """
        refresh_data = {}

        response: Response = await make_post_request("/api/refresh/", json=refresh_data)

        # Проверка статуса ответа
        assert response.status_code == 422, f"Ожидался статус 422, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_refresh_after_logout(self, make_post_request, auth_tokens):
        """
        Тест обновления токена после logout.
        Refresh токен должен быть недействительным после logout.
        """
        # Сначала выполняем logout
        logout_data = {
            "refresh_token": auth_tokens["refresh_token"]
        }
        logout_response: Response = await make_post_request("/api/logout/", json=logout_data)
        assert logout_response.status_code == 200, "Ошибка при logout"

        # Пытаемся обновить токен
        refresh_data = {
            "refresh_token": auth_tokens["refresh_token"]
        }
        response: Response = await make_post_request("/api/refresh/", json=refresh_data)

        # Проверка статуса ответа - токен должен быть недействителен
        assert response.status_code == 401, f"Ожидался статус 401, получен {response.status_code}"


class TestAuthLogout:
    """Тесты для эндпоинта выхода (POST /api/logout/)"""

    @pytest.mark.asyncio
    async def test_logout_success(self, make_post_request, auth_tokens):
        """
        Тест успешного выхода из системы.
        После logout refresh токен должен стать недействительным.
        """
        logout_data = {
            "refresh_token": auth_tokens["refresh_token"]
        }

        response: Response = await make_post_request("/api/logout/", json=logout_data)

        # Проверка статуса ответа
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, make_post_request):
        """
        Тест выхода с невалидным refresh токеном.
        Должен вернуть ошибку 401 или 400.
        """
        logout_data = {
            "refresh_token": "invalid_token_12345"
        }

        response: Response = await make_post_request("/api/logout/", json=logout_data)

        # Проверка статуса ответа (может быть 400 или 401 в зависимости от реализации)
        assert response.status_code in [400, 401], f"Ожидался статус 400 или 401, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_logout_missing_token(self, make_post_request):
        """
        Тест выхода без передачи refresh_token.
        Должен вернуть ошибку валидации 422.
        """
        logout_data = {}

        response: Response = await make_post_request("/api/logout/", json=logout_data)

        # Проверка статуса ответа
        assert response.status_code == 422, f"Ожидался статус 422, получен {response.status_code}"

    @pytest.mark.asyncio
    async def test_double_logout(self, make_post_request, auth_tokens):
        """
        Тест двойного logout с одним и тем же токеном.
        Второй logout должен завершиться с ошибкой, так как токен уже отозван.
        """
        logout_data = {
            "refresh_token": auth_tokens["refresh_token"]
        }

        # Первый logout
        response1: Response = await make_post_request("/api/logout/", json=logout_data)
        assert response1.status_code == 200, "Ошибка при первом logout"

        # Второй logout с тем же токеном
        response2: Response = await make_post_request("/api/logout/", json=logout_data)

        # Проверка статуса ответа - токен уже отозван
        assert response2.status_code in [400, 401], f"Ожидался статус 400 или 401, получен {response2.status_code}"


class TestAuthFlow:
    """Интеграционные тесты для полного flow авторизации"""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self, make_post_request, test_user_data):
        """
        Тест полного цикла авторизации:
        1. Login - получение токенов
        2. Refresh - обновление access токена
        3. Logout - выход из системы
        """
        # 1. Login
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        login_response: Response = await make_post_request("/api/login/", json=login_data)
        assert login_response.status_code == 200, "Ошибка при login"
        tokens = login_response.json()

        # 2. Refresh
        refresh_data = {
            "refresh_token": tokens["refresh_token"]
        }
        refresh_response: Response = await make_post_request("/api/refresh/", json=refresh_data)
        assert refresh_response.status_code == 200, "Ошибка при refresh"
        new_access_token = refresh_response.json()["access_token"]
        assert new_access_token != tokens["access_token"], "Access токен не обновился"

        # 3. Logout
        logout_data = {
            "refresh_token": tokens["refresh_token"]
        }
        logout_response: Response = await make_post_request("/api/logout/", json=logout_data)
        assert logout_response.status_code == 200, "Ошибка при logout"

        # 4. Проверка, что после logout refresh не работает
        refresh_after_logout: Response = await make_post_request("/api/refresh/", json=refresh_data)
        assert refresh_after_logout.status_code == 401, "Refresh токен должен быть недействителен после logout"
