"""
Утилиты для работы со временем.
Предоставляет функции для получения текущего времени в UTC.
"""
import datetime


def utc_now() -> datetime.datetime:
    """
    Возвращает текущее время в UTC timezone.
    Используется для записи временных меток в БД.
    """
    return datetime.datetime.now(datetime.UTC)