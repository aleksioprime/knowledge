Используется для определения параметров запроса. Параметры запроса передаются в URL-адресе после знака вопроса (`?`), например:  `/items?item_id=123`

Общие метаданные:

- `title`: Описание параметра, отображаемое в документации.
- `description`**:** Более подробное описание параметра.
- `examples`**:** Пример значения параметра.
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
from typing import Annotated
from fastapi import FastAPI, Path, Query

app = FastAPI()

@app.get("/user/{username}")
async def login(
		username: Annotated[
			str, Path(min_length=3, max_length=15, description='Enter your username', example='permin0ff')],
		first_name: Annotated[str | None, Query(max_length=10)] = None) -> dict: 
	return {"user": username, "Name": first_name}
```

Для Python 3.10 и выше мы можем сделать параметр не обязательным, указав:

```python
first_name: Annotated[str | None, Query()] = None)
```

Когда `Query` используется внутри `Annotated`, вы не можете использовать параметр `default` у `Query`. Вместо этого, используйте обычное указание значения по умолчанию для параметра функции. 

```python
first_name: Annotated[str | None, Query()] = "Tomas")
```

В случае, чтобы сделать параметр `Query` обязательным, вы можете просто не указывать значение по умолчанию, или установить параметр `default` равным многоточию `...`:

```python
first_name: Annotated[str, Query(max_length=10)] = ...)
```

С помощью параметра `include_in_schema` мы можем исключить данный параметр из документации.

```python
first_name: str | None = Query(default=None, include_in_schema=False)
```

С помощью класса Query можно запрашивать списки через строку запроса. Обычно списки значений появляются, когда в строке запроса один и тот же параметр повторяется с разными значениями.

```python
@app.get("/user")
async def search(people: Annotated[list[str], Query()]) -> dict: 
	return {"user": people}
```

Классы `Path()` и `Query()` в FastAPI позволяют определить параметр `pattern` для проверки, чтобы можно было проверить строковое значение параметра пути/запроса по указанному шаблону поиска.

```python
@app.get("/user/{username}")
async def login(
		username: Annotated[ str, Path(min_length=3, max_length=15, description='Enter your username', example='permin0ff')],
		first_name: Annotated[ str | None, Query(max_length=10, pattern="^J|s$")] = None) -> dict: 
	return {"user": username, "Name": first_name}
```