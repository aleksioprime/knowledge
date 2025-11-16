Класс `APIRouter` принадлежит пакету FastAPI и создает операции пути для нескольких маршрутов. 

Класс **`APIRouter`** в FastAPI позволяет **организовать и структурировать API-эндпойнты**, делая их **модульными, переиспользуемыми и легко настраиваемыми**.

Он используется для **группировки маршрутов (роутов)** внутри отдельных файлов или модулей, что упрощает поддержку кода и регистрацию маршрутов в основном `FastAPI` приложении.

Класс APIRouter работает так же, как и класс FastAPI. Однако `uvicorn` не может использовать экземпляр APIRouter для обслуживания приложения, в отличие от FastAPI.

```python
from fastapi import APIRouter

router = APIRouter(prefix='/categories', tags=['category'])

@router.get('/')
async def get_all_categories():
    pass

@router.post('/')
async def create_category():
    pass

@router.put('/{category_id}')
async def update_category(category_id: int):
    pass

@router.delete('/{category_id}')
async def delete_category(category_id: int):
    pass
```

 Добавлен дополнительный префикс пути для маршрутизатора для группировки операций параметра пути `/category`, и также параметр `tags`,  он отвечает за список тегов, которые будут применены ко всем операциям пути в этом маршрутизаторе, для группировки в документации.

Маршруты, определенные с помощью класса APIRouter, добавляются в экземпляр FastAPI для обеспечения их видимости. Для этого существует метод `include_router()`, который отвечает за добавление маршрутов, определенных с помощью класса APIRouter, в экземпляр основного приложения, чтобы сделать маршруты видимыми.

```python
from fastapi import FastAPI
from app.routers import category

app = FastAPI()


@app.get("/")
async def welcome() -> dict:
    return {"message": "My e-commerce app"}


app.include_router(category.router)
```

