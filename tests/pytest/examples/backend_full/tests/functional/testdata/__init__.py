"""
Модуль для загрузки тестовых данных из JSON файлов.
"""
import json
from pathlib import Path


def load_test_data(filename: str):
    """Загружает тестовые данные из JSON файла"""
    data_dir = Path(__file__).parent
    file_path = data_dir / filename
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
