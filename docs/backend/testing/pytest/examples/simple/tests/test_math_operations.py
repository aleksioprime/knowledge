"""Тесты математических операций с группировкой и параметризацией"""
import pytest
from app.math_operations import add, subtract, multiply, divide, power


class TestMathOperations:
    """Группировка тестов для математических операций"""

    def test_add(self):
        """Тест сложения"""
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0, 0) == 0

    def test_subtract(self):
        """Тест вычитания"""
        assert subtract(5, 3) == 2
        assert subtract(10, 10) == 0
        assert subtract(-5, -3) == -2

    def test_multiply(self):
        """Тест умножения"""
        assert multiply(3, 4) == 12
        assert multiply(-2, 5) == -10
        assert multiply(0, 100) == 0

    def test_divide(self):
        """Тест деления"""
        assert divide(10, 2) == 5
        assert divide(7, 2) == 3.5
        assert divide(-10, 5) == -2

    def test_divide_by_zero(self):
        """Тест деления на ноль - проверка исключения"""
        with pytest.raises(ZeroDivisionError) as exc_info:
            divide(10, 0)
        assert "Деление на ноль невозможно" in str(exc_info.value)

    def test_power(self):
        """Тест возведения в степень"""
        assert power(2, 3) == 8
        assert power(5, 2) == 25
        assert power(10, 0) == 1


@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (10, 5, 15),
    (-1, 1, 0),
    (0, 0, 0),
    (100, -50, 50),
])
def test_add_parametrize(a, b, expected):
    """Параметризованный тест сложения"""
    assert add(a, b) == expected


@pytest.mark.parametrize("a,b,expected", [
    (10, 2, 5.0),
    (7, 2, 3.5),
    (-10, 5, -2.0),
    (0, 1, 0.0),
])
def test_divide_parametrize(a, b, expected):
    """Параметризованный тест деления"""
    assert divide(a, b) == expected
