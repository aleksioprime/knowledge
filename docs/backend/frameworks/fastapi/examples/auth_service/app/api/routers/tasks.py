from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.models import User

# Задачи живут в другом сервисе. Эндпоинт здесь — только чтобы показать
# require_permission на знакомом примере и проверить его тестом.
router = APIRouter(prefix='/tasks', tags=['demo'])


@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: Annotated[User, Depends(require_permission('tasks:delete'))]) -> None:
    pass
