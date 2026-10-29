from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ISSUER = 'http://localhost:8080/realms/tasker'
AUDIENCE = 'tasker-api'

# Открытые ключи Keycloak: клиент скачает их один раз и закэширует
jwks_client = jwt.PyJWKClient(f'{ISSUER}/protocol/openid-connect/certs')
bearer = HTTPBearer()

app = FastAPI(title='Задачи с Keycloak')


def get_claims(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> dict:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=['RS256'], audience=AUDIENCE, issuer=ISSUER)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=f'Неверный токен: {error}')


Claims = Annotated[dict, Depends(get_claims)]


def require_role(role: str):
    def checker(claims: Claims) -> dict:
        if role not in claims.get('realm_access', {}).get('roles', []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f'Нужна роль {role}')
        return claims
    return checker


@app.get('/me')
def me(claims: Claims) -> dict:
    return {
        'id': claims['sub'],
        'username': claims['preferred_username'],
        'roles': sorted(claims['realm_access']['roles']),
    }


@app.delete('/admin/tasks', dependencies=[Depends(require_role('admin'))])
def clear_all_tasks() -> dict:
    return {'deleted': 'все задачи'}
