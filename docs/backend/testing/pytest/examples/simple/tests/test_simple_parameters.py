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

    # @pytest.mark.parametrize(
    #     "text,search_element",
    #     [(123, 456), (123, None), (True, 456), (True, None), (TEST_TEXT, 456), (TEST_TEXT, None)],
    # )
    @pytest.mark.parametrize("search_element", [456, None])
    @pytest.mark.parametrize("text", [123, True, TEST_TEXT])
    def test_non_string_arguments(self, text, search_element):
        """Передача нестроковых аргументов"""
        # Act
        with pytest.raises(TypeError) as exc_info:
            find_elem_index(text, search_element)
        # Assert
        assert "Оба аргумента должны быть строками" in str(exc_info.value)