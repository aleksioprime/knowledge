"""Примеры использования маркировок pytest"""
import pytest
import sys


# Простой пропуск теста
@pytest.mark.skip(reason="Тест еще не реализован")
def test_not_implemented():
    """Этот тест будет пропущен"""
    assert False


# Условный пропуск теста
@pytest.mark.skipif(sys.platform == "win32", reason="Не работает на Windows")
def test_unix_specific():
    """Тест только для Unix-систем"""
    assert sys.platform != "win32"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Требуется Python 3.10+")
def test_new_python_feature():
    """Тест для новых версий Python"""
    assert sys.version_info >= (3, 10)


# Ожидаемый провал
@pytest.mark.xfail(reason="Известная баг, ожидается исправление")
def test_known_bug():
    """Тест с известным багом"""
    assert 1 + 1 == 3  # Баг: неправильный результат


@pytest.mark.xfail(sys.platform == "darwin", reason="Не работает на macOS")
def test_platform_specific():
    """Тест с ожидаемым провалом на определенной платформе"""
    assert False


# Пользовательские маркировки
@pytest.mark.slow
def test_slow_operation():
    """Медленный тест - можно пропустить при быстром запуске"""
    import time
    time.sleep(0.1)  # Имитация долгой операции
    assert True


@pytest.mark.slow
def test_another_slow_operation():
    """Еще один медленный тест"""
    import time
    time.sleep(0.1)
    assert True


@pytest.mark.fast
def test_fast_operation():
    """Быстрый тест"""
    assert 1 + 1 == 2


@pytest.mark.integration
def test_integration():
    """Интеграционный тест"""
    # Имитация интеграционного теста
    assert True


@pytest.mark.unit
def test_unit():
    """Юнит-тест"""
    assert 2 * 2 == 4


# Множественные маркировки
@pytest.mark.slow
@pytest.mark.integration
def test_slow_integration():
    """Тест с несколькими маркировками"""
    import time
    time.sleep(0.1)
    assert True


# Маркировка класса
@pytest.mark.database
class TestDatabase:
    """Все тесты в классе будут помечены как 'database'"""

    def test_connection(self):
        """Тест подключения к БД"""
        assert True

    def test_query(self):
        """Тест запроса к БД"""
        assert True

    @pytest.mark.slow
    def test_slow_query(self):
        """Медленный запрос - дополнительная маркировка"""
        import time
        time.sleep(0.1)
        assert True


# Параметризация с маркировками
@pytest.mark.parametrize("x,y,expected", [
    pytest.param(1, 2, 3, marks=pytest.mark.fast),
    pytest.param(10, 20, 30, marks=pytest.mark.slow),
    pytest.param(100, 200, 300, marks=[pytest.mark.slow, pytest.mark.integration]),
])
def test_addition_with_marks(x, y, expected):
    """Параметризованный тест с разными маркировками"""
    assert x + y == expected


# Условный xfail
@pytest.mark.xfail(sys.platform == "win32", reason="Баг на Windows")
def test_conditional_xfail():
    """Тест с условным ожидаемым провалом"""
    assert sys.platform != "win32"
