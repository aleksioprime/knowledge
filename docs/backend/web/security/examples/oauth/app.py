import os

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.sessions import SessionMiddleware

KEYCLOAK_URL = os.environ.get('KEYCLOAK_URL', 'http://localhost:8080')
ISSUER = f'{KEYCLOAK_URL}/realms/tasker-oauth'

app = FastAPI(title='Вход через внешний сервис')
# Сессия в подписанной cookie: здесь живут state, nonce и code_verifier между редиректами
app.add_middleware(SessionMiddleware, secret_key=os.environ.get('SESSION_SECRET', 'dev-only-session-secret'))

oauth = OAuth()
oauth.register(
    name='keycloak',
    client_id='tasker-web',
    client_secret=os.environ.get('CLIENT_SECRET', 'tasker-web-test-secret'),
    server_metadata_url=f'{ISSUER}/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile', 'code_challenge_method': 'S256'},
)

# Вместо таблицы social_account: (provider, provider_user_id) -> id пользователя «Задачника»
social_accounts: dict[tuple[str, str], int] = {}
users: dict[int, dict] = {}


@app.get('/login')
async def login(request: Request):
    redirect_uri = str(request.url_for('auth_callback'))
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@app.get('/auth/callback')
async def auth_callback(request: Request):
    try:
        # Проверяет state, обменивает code на токены с code_verifier,
        # проверяет подпись id_token по JWKS, iss, aud, exp и nonce
        token = await oauth.keycloak.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(400, detail=f'{error.error}: {error.description}')

    claims = token['userinfo']
    key = ('keycloak', claims['sub'])
    if key not in social_accounts:
        user_id = len(users) + 1
        users[user_id] = {'id': user_id, 'email': claims.get('email'), 'name': claims.get('name')}
        social_accounts[key] = user_id
    user = users[social_accounts[key]]

    request.session['user_id'] = user['id']
    return {'user': user, 'id_token_claims': dict(claims), 'scope': token.get('scope')}


@app.get('/me')
async def me(request: Request):
    user_id = request.session.get('user_id')
    if user_id is None:
        raise HTTPException(401, detail='Не выполнен вход')
    return users[user_id]
