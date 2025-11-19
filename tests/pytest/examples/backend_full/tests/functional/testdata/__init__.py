"""
Модуль для загрузки тестовых данных из JSON файлов.
Предоставляет утилиты для работы с тестовыми данными пользователей, items и т.д.
"""
import json
from pathlib import Path
from typing import Any, Dict, List


class TestDataLoader:
    """Класс для загрузки тестовых данных из JSON файлов"""

    def __init__(self):
        self.data_dir = Path(__file__).parent

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Загружает данные из JSON файла"""
        file_path = self.data_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_users(self) -> List[Dict[str, Any]]:
        """Возвращает список тестовых пользователей"""
        data = self.load_json('users.json')
        return data.get('users', [])

    def get_user_by_username(self, username: str) -> Dict[str, Any] | None:
        """Возвращает данные пользователя по username"""
        users = self.get_users()
        for user in users:
            if user['username'] == username:
                return user
        return None

    def get_admin_user(self) -> Dict[str, Any] | None:
        """Возвращает первого админ-пользователя"""
        users = self.get_users()
        for user in users:
            if user.get('is_admin', False):
                return user
        return None

    def get_regular_user(self) -> Dict[str, Any] | None:
        """Возвращает первого обычного пользователя"""
        users = self.get_users()
        for user in users:
            if not user.get('is_admin', False):
                return user
        return None

    def get_items(self) -> List[Dict[str, Any]]:
        """Возвращает список тестовых items"""
        data = self.load_json('items.json')
        return data.get('items', [])

    def get_groups(self) -> List[Dict[str, Any]]:
        """Возвращает список тестовых групп"""
        data = self.load_json('items.json')
        return data.get('groups', [])

    def get_tags(self) -> List[Dict[str, Any]]:
        """Возвращает список тестовых тегов"""
        data = self.load_json('items.json')
        return data.get('tags', [])

    def get_item_by_name(self, name: str) -> Dict[str, Any] | None:
        """Возвращает данные item по названию"""
        items = self.get_items()
        for item in items:
            if item['name'] == name:
                return item
        return None


# Создаем глобальный экземпляр загрузчика
test_data_loader = TestDataLoader()
