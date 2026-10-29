def find_elem_index(text: str, element: str, case_sensitive: bool = True) -> int:
    """
    Находит индекс первого вхождения `element` в `text`.

    Args:
        text: строка для поиска
        element: подстрока для нахождения
        case_sensitive: учитывать регистр (по умолчанию True)
    """
    if not isinstance(text, str) or not isinstance(element, str):
        raise TypeError("Оба аргумента должны быть строками")

    if not case_sensitive:
        text = text.lower()
        element = element.lower()

    return text.index(element)