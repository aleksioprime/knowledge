import pytest
from app.extention_example import find_elem_index

class TestFindElemIndex:
    """Тесты функции find_elem_index с применением AAA подхода"""
    TEST_TEXT = "abcdef"

    def test_find_existing_element(self):
        """Нахождение существующего элемента"""
        # Arrange
        search_element = "c"
        expected_index = 2

        # Act
        result = find_elem_index(self.TEST_TEXT, search_element)

        # Assert
        assert result == expected_index

    def test_find_int(self):
        """Проверка с некорректным типом аргумента"""
        # Arrange
        search_element = 123

        # Act
        with pytest.raises(TypeError) as exc_info:
            find_elem_index(self.TEST_TEXT, search_element)

        # Assert
        assert str(exc_info.value) == "Оба аргумента должны быть строками"