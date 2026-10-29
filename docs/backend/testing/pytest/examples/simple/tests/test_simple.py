from app.example import find_elem_index, find_elem_index_with_check
import pytest

def test_find_elem_index():
    """Проверка функции find_elem_index"""
    assert find_elem_index("abcdef", "c") == 2


# def test_find_elem_index_incorrect():
#     """Проверка функции find_elem_index с неправильным ожидаемым результатом"""
#     assert find_elem_index("abcdef", "c") == 3, "Индекс не совпадает с ожидаемым"


def test_find_int():
    """Проверка с некорректным типом аргумента"""
    with pytest.raises(TypeError) as exc_info:
        find_elem_index_with_check("abcdef", 123)
    assert str(exc_info.value) == "Оба аргумента должны быть строками"