def find_elem_index(text: str, element: str) -> int:
    """Находит индекс первого вхождения element в text."""
    return text.index(element)

def find_elem_index_with_check(text: str, element: str) -> int:
    """Находит индекс первого вхождения `element` в `text`."""
    if not isinstance(text, str) or not isinstance(element, str):  # <-- добавим проверку на типы данных
        raise TypeError("Оба аргумента должны быть строками")
    return text.index(element)