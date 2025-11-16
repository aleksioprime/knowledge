"""Математические операции для демонстрации тестирования"""


def add(a: int | float, b: int | float) -> int | float:
    """Сложение двух чисел"""
    return a + b


def subtract(a: int | float, b: int | float) -> int | float:
    """Вычитание двух чисел"""
    return a - b


def multiply(a: int | float, b: int | float) -> int | float:
    """Умножение двух чисел"""
    return a * b


def divide(a: int | float, b: int | float) -> float:
    """
    Деление двух чисел

    Raises:
        ZeroDivisionError: если делитель равен нулю
    """
    if b == 0:
        raise ZeroDivisionError("Деление на ноль невозможно")
    return a / b


def power(base: int | float, exponent: int) -> int | float:
    """Возведение в степень"""
    return base ** exponent
