Используется для определения параметров пути в маршрутах и накладывает правила валидации, улучшая работу с API. Класс `Path` также помогает дать параметрам маршрута больше контекста во время документации, автоматически предоставляемой `OpenAPI` через `Swagger` и `ReDoc`, и действует как валидатор.

Path-параметр всегда является **обязательным**, поскольку он составляет часть пути!

Через конструктор Path можно установить следующие параметры для валидации значений:

Общие метаданные:

- `title`: Описание параметра, отображаемое в документации.
- `description`**:** Более подробное описание параметра.
- `example`**:** Пример значения параметра.
- `include_in_schema`: Параметр позволяет исключить операцию пути из сгенерированной схемы OpenAPI

Специфичные правила валидации:

- `min_length`: Минимальная длина строки для параметра.
- `max_length`:  Максимальная длина строки для параметра.
- `pattern`: Устанавливает регулярное выражение, которому должно соответствовать значение параметра
- `lt`: Значение должно быть меньше указанного.
- `le`: Значение должно быть меньше или равно указанному.
- `gt`: Значение должно быть больше указанного.
- `ge`:Значение должно быть больше или равно указанному.


```python
from fastapi import FastAPI, Path

app = FastAPI()

@app.get("/user/{username}/{age}")
async def login(
	username: str = Path(min_length=3, max_length=15, description='Enter your username', example='Ilya'),
	age: int = Path(ge=0, le=100, description="Enter your age"),
	) -> dict:
	return {"user": username, "age": age}
```

Чтобы параметр без значения по умолчанию мог идти после `Path` нужно использовать класс `Annotated` 

```python
@app.get("/user/{username}")
async def login(
	username: Annotated[ str, Path(min_length=3, max_length=15, description='Enter your username', example='Ilya')],
	age: int,) -> dict:
	return {"user": username, "age": age}
```