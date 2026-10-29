"""Проходит вход целиком, как браузер: редиректы, cookie, форма логина Keycloak."""
import html
import re
from urllib.parse import parse_qs, urlsplit

import httpx

APP = 'http://localhost:8000'
USERNAME, PASSWORD = 'anna', 'secret123'
CLIENT_ID, CLIENT_SECRET = 'tasker-web', 'tasker-web-test-secret'


def show_query(title: str, url: str) -> None:
    print(f'\n{title}: {url.split("?")[0]}')
    for name, values in parse_qs(urlsplit(url).query).items():
        print(f'  {name} = {values[0]}')


def sign_in(browser: httpx.Client, verbose: bool) -> tuple[str, str]:
    """Нажимает «Войти» и заполняет форму Keycloak. Возвращает адрес провайдера и callback-URL."""
    authorize_url = browser.get(f'{APP}/login').headers['location']
    if verbose:
        show_query('1. Редирект на провайдера', authorize_url)

    page = browser.get(authorize_url)
    action = html.unescape(re.search(r'<form[^>]+action="([^"]+)"', page.text).group(1))
    # Keycloak ставит cookie с флагом Secure. Браузер считает localhost безопасным
    # и отправляет их даже по http, а httpx — нет, поэтому передаём их явно
    keycloak_cookies = '; '.join(f'{c.name}={c.value}' for c in browser.cookies.jar if c.secure)
    response = browser.post(action, data={'username': USERNAME, 'password': PASSWORD},
                            headers={'Cookie': keycloak_cookies})
    callback_url = response.headers['location']
    if verbose:
        show_query('2. Провайдер возвращает на redirect_uri', callback_url)
    return authorize_url, callback_url


def steal_code(authorize_url: str, callback_url: str) -> httpx.Response:
    """Атакующий перехватил code и даже знает client_secret, но не знает code_verifier."""
    token_url = authorize_url.split('?')[0].removesuffix('/auth') + '/token'
    code = parse_qs(urlsplit(callback_url).query)['code'][0]
    return httpx.post(token_url, data={
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': f'{APP}/auth/callback',
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
    })


with httpx.Client(follow_redirects=False, timeout=10) as browser:
    authorize_url, callback_url = sign_in(browser, verbose=True)

    # 3. Браузер приходит в приложение с code и state, приложение меняет code на токены
    response = browser.get(callback_url)
    print('\n3. Ответ приложения:', response.status_code)
    print(response.text)

    print('\n4. /me с cookie сессии:', browser.get(f'{APP}/me').text)

    response = browser.get(callback_url)
    print('\n5. Тот же callback ещё раз:', response.status_code, response.text)

    response = steal_code(authorize_url, callback_url)
    print('\n6. Уже использованный code напрямую у провайдера:', response.status_code, response.text)

# 7. Чужой callback в браузере жертвы, у которой в сессии нет такого state (login CSRF)
with httpx.Client(timeout=10) as victim:
    response = victim.get(callback_url)
    print('\n7. Callback без своего state:', response.status_code, response.text)

# 8. Свежий code перехвачен до того, как его использовало приложение
with httpx.Client(follow_redirects=False, timeout=10) as browser:
    authorize_url, callback_url = sign_in(browser, verbose=False)
    response = steal_code(authorize_url, callback_url)
    print('\n8. Свежий code без code_verifier:', response.status_code, response.text)
