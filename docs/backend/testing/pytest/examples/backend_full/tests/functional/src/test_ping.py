import pytest
from httpx import AsyncClient


class TestPingAPI:
    endpoint_template = "/api/ping/"

    @pytest.mark.asyncio
    async def test_ping(self, make_get_request):
        """
        Тестирует эндпоинт для проверки состояния сервера
        """
        endpoint = f"{self.endpoint_template}"

        response = await make_get_request(endpoint)

        # Проверка статуса ответа
        assert response.status_code == 200, f"Статус ответа должен быть 200, пришёл {response.status_code}"
        assert response.json() == {"status": "ok", "message": "Server is up and running"}