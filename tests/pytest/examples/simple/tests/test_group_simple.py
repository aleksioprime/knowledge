from app.example import find_elem_index_with_check
import pytest


class TestFindElemIndex:
    """Тесты функции find_elem_index"""
    TEST_TEXT = "abcdef"

    def test_find_existing_element(self):
        """Проверка функции find_elem_index"""
        assert find_elem_index_with_check(self.TEST_TEXT, "c") == 2

    def test_find_int(self):
        """Проверка с некорректным типом аргумента"""
        with pytest.raises(TypeError) as exc_info:
            find_elem_index_with_check(self.TEST_TEXT, 123)
        assert str(exc_info.value) == "Оба аргумента должны быть строками"