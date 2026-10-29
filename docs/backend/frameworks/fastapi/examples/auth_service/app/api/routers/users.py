from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_permission
from app.models import User
from app.schemas import UserOut
from app.services import users

router = APIRouter(prefix='/users', tags=['users'])


@router.put('/{user_id}/roles/{role_name}', dependencies=[Depends(require_permission('roles:manage'))])
async def set_role(session: SessionDep, user_id: int, role_name: str) -> UserOut:
    user = await session.get(User, user_id)
    role = await users.get_role(session, role_name)
    if user is None or role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Нет такого пользователя или роли')
    user.roles = [role]
    await session.commit()
    return UserOut(id=user.id, email=user.email, roles=user.role_names)
