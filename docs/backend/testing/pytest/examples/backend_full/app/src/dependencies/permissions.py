from fastapi import Depends, HTTPException, Request, status

from src.schemas.auth import UserJWT
from src.core.security import JWTBearer


def permission_required(
    admin: bool = False,
    allow_self: bool = False,
    user_id_param: str = "user_id",
):
    """
    Декоратор для проверки прав доступа пользователя к эндпоинту

    Args:
        admin: Требуется ли права администратора
        allow_self: Разрешить доступ к собственным данным
        user_id_param: Имя параметра пути с user_id для проверки allow_self
    """
    def checker(
        user: UserJWT = Depends(JWTBearer()),
        request: Request = None,
    ):
        # Если требуются права администратора
        if admin:
            if not getattr(user, "is_admin", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав. Требуются права администратора"
                )
            return user

        # Если разрешен доступ к собственным данным
        if allow_self:
            user_id = request.path_params.get(user_id_param)
            if str(user.id) == str(user_id):
                return user
            # Если не совпадает, но пользователь админ - тоже разрешаем
            if getattr(user, "is_admin", False):
                return user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав"
            )

        # Если не требуется ни админ, ни allow_self - просто аутентифицированный пользователь
        return user

    return checker