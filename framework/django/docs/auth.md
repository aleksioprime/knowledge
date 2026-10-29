# Django: пользователи и внешняя аутентификация

Встроенный `User` в Django годится, пока хватает его полей и пароли хранит сам Django. Обычно рано или поздно нужно больше: войти по email, хранить id пользователя из другой системы или вообще проверять пароль не у себя, а в отдельном [Auth-сервисе](../../fast_api/docs/auth_sessions.md). Для первого Django даёт свою модель пользователя, для второго — бэкенды аутентификации.

Код ниже проверен на копии [учебного проекта](../example/README.md) с добавленным приложением `users`. В самом примере его нет.

```bash
pip install httpx
```

## Минимальный пример

```python
# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # id пользователя в Auth-сервисе; у локальных аварийных админов его нет
    external_id = models.PositiveIntegerField('id в Auth-сервисе', unique=True, null=True, blank=True)
```

```python
# config/settings.py
INSTALLED_APPS = [..., 'users']
AUTH_USER_MODEL = 'users.User'
```

```bash
python manage.py makemigrations users
python manage.py migrate
```

Теперь `request.user`, админка, `createsuperuser` и внешние ключи на `settings.AUTH_USER_MODEL` работают с моделью `users.User`.

## Своя модель пользователя

Три способа добавить пользователю данные:

| Способ | Что это | Когда |
|---|---|---|
| `AbstractUser` | наследник со всеми полями стандартного `User` (`username`, `email`, `is_staff`, группы, права) | почти всегда: нужны дополнительные поля, а вход по `username` устраивает |
| `AbstractBaseUser` + `PermissionsMixin` + свой менеджер | только пароль и `last_login`, остальное описываете сами | вход по email или телефону, нет `username`, другая структура полей |
| Профиль `OneToOneField(User)` | отдельная таблица рядом со стандартным `User` | проект уже живёт со стандартной моделью, а данные профиля нужны не везде |

`AbstractBaseUser` требует больше кода: указать `USERNAME_FIELD`, `REQUIRED_FIELDS` и написать менеджер с `create_user` и `create_superuser`, которые вызывает `createsuperuser`:

```python
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **fields):
        user = self.model(email=self.normalize_email(email), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **fields):
        return self.create_user(email, password, is_staff=True, is_superuser=True, **fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
```

Профиль — самый безболезненный способ для существующего проекта, но каждое обращение к его полям — лишний JOIN или запрос (`select_related('profile')`), а профиль нужно создавать при регистрации, обычно [сигналом](signals.md) `post_save`.

### Заводите свою модель в начале проекта

Даже если поля не нужны, начинайте с пустого `class User(AbstractUser): pass`. Поменять `AUTH_USER_MODEL` в проекте, где миграции уже применены, почти невозможно. На копии учебного проекта после `migrate` со стандартной моделью и переключения на `users.User`:

```bash
python manage.py migrate
# django.db.migrations.exceptions.InconsistentMigrationHistory:
#   Migration admin.0001_initial is applied before its dependency users.0001_initial on database 'default'.
```

Таблица `auth_user` уже существует, на неё ссылаются внешние ключи всех приложений и записи `django_migrations`. Переезд — это ручной перенос данных и правка истории миграций. С пустой моделью с первого дня любое поле потом добавляется обычной миграцией.

### `get_user_model()` и `settings.AUTH_USER_MODEL`

Код не должен импортировать `django.contrib.auth.models.User` напрямую: после замены модели он сломается. Тесты учебного проекта делают именно так, и после переключения на `users.User` все шесть падают:

```text
AttributeError: Manager isn't available; 'auth.User' has been swapped for 'users.User'
```

Правило простое:

- в **моделях** (внешние ключи) — строка `settings.AUTH_USER_MODEL`: модели ещё не загружены, когда описываются связи;
- **в остальном коде** — `get_user_model()`, она вернёт текущий класс.

```python
from django.conf import settings
from django.contrib.auth import get_user_model

owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

User = get_user_model()
User.objects.create_user('anna', password='secret123')
```

Админка для своей модели — наследник `UserAdmin`, иначе форма покажет хэш пароля как обычное поле:

```python
# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AppUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'external_id', 'is_staff', 'is_superuser', 'last_login')
    fieldsets = UserAdmin.fieldsets + (('Auth-сервис', {'fields': ('external_id',)}),)
```

## Бэкенды аутентификации

`django.contrib.auth.authenticate(request, username=..., password=...)` сама пароль не проверяет. Она по очереди спрашивает бэкенды из `AUTHENTICATION_BACKENDS`. Бэкенд — класс с двумя методами:

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend


class EmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        user = User.objects.filter(email=username).first()
        if user and user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        return get_user_model().objects.filter(pk=user_id, is_active=True).first()
```

- **`authenticate`** проверяет учётные данные и возвращает пользователя или `None` («не мой случай, спросите следующего»).
- **`get_user`** восстанавливает пользователя по id из сессии. После входа Django запоминает в сессии `_auth_user_id` и путь к бэкенду (`_auth_user_backend`), и на каждом запросе `AuthenticationMiddleware` вызывает `get_user` именно этого бэкенда. Поэтому бэкенд нельзя просто удалить из настроек: пользователи, которые вошли через него, окажутся анонимными.

Как идёт перебор:

```python
AUTHENTICATION_BACKENDS = [
    'users.backends.AuthServiceBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

1. Бэкенды вызываются **в порядке списка**; первый, кто вернул пользователя, побеждает.
2. `None` — перейти к следующему.
3. Исключение **`PermissionDenied`** — остановить перебор: следующие бэкенды не вызываются, `authenticate` вернёт `None` и отправит сигнал `user_login_failed`. Это способ сказать «я точно знаю, что этот вход запрещён».
4. Бэкенд, у которого `authenticate` не принимает переданные аргументы, пропускается.

Проверка прав (`user.has_perm('tasks.delete_task')`) тоже опрашивает все бэкенды. Права из групп и `user_permissions` умеет считать `ModelBackend`. Поэтому свой бэкенд удобно наследовать от него: `get_user` и права достаются бесплатно, переопределяется только `authenticate`.

## Вход в админку через Auth-сервис

Пользователи, пароли и роли живут в [Auth-сервисе на FastAPI](../../fast_api/examples/auth_service/README.md). Django-админка пароли не хранит, но должна пускать менеджеров и администраторов. План бэкенда:

1. отправить email и пароль в `POST /auth/login`;
2. получить профиль и роли из `GET /auth/me`, затем закрыть полученную сессию в Auth-сервисе;
3. создать или обновить локального пользователя (без пароля) и перевести роль в `is_staff` / `is_superuser` / группы;
4. если Auth-сервис недоступен — не пустить и не упасть с 500.

```python
# users/backends.py
import logging

import httpx
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

# роль в Auth-сервисе → группа с правами в админке
ROLE_GROUPS = {'manager': 'Менеджеры'}


def user_agent(request) -> str:
    return request.META.get('HTTP_USER_AGENT', 'django-admin') if request is not None else 'django-admin'


class AuthServiceBackend(ModelBackend):
    transport: httpx.BaseTransport | None = None  # в тестах подменяется на MockTransport

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            profile = self._fetch_profile(username, password, user_agent(request))
        except httpx.HTTPError:
            logger.exception('Auth-сервис недоступен')
            if request is not None:
                messages.error(request, 'Сервис авторизации недоступен, попробуйте позже')
            return None  # дальше попробует ModelBackend: войдут только локальные аварийные админы
        if profile is None:
            # Auth-сервис сказал «неверный пароль»: не даём ModelBackend проверить
            # старый локальный пароль с тем же логином
            raise PermissionDenied
        user = self._sync_user(profile)
        return user if self.user_can_authenticate(user) else None

    def _fetch_profile(self, email: str, password: str, user_agent: str) -> dict | None:
        with httpx.Client(
            base_url=settings.AUTH_SERVICE_URL, timeout=settings.AUTH_SERVICE_TIMEOUT, transport=self.transport,
        ) as client:
            # иначе в истории входов будет User-Agent Django-сервера, а не браузера
            response = client.post(
                '/auth/login', json={'email': email, 'password': password}, headers={'User-Agent': user_agent},
            )
            if response.status_code in (401, 422):
                return None
            response.raise_for_status()
            auth = {'Authorization': f'Bearer {response.json()["access_token"]}'}
            me = client.get('/auth/me', headers=auth)
            me.raise_for_status()
            # токены нужны были один раз: закрываем сессию, чтобы она не висела в Auth-сервисе
            client.post('/auth/logout', headers=auth)
            return me.json()

    def _sync_user(self, profile: dict):
        User = get_user_model()
        roles = set(profile['roles'])
        user = (
            User.objects.filter(external_id=profile['id']).first()
            # локальный пользователь с тем же логином: привязываем, а не падаем на unique
            or User.objects.filter(username=profile['email'], external_id=None).first()
            or User()
        )
        if user.external_id is None:
            user.external_id = profile['id']
            user.set_unusable_password()  # пароль знает только Auth-сервис
        user.username = user.email = profile['email']
        user.is_superuser = 'admin' in roles
        user.is_staff = user.is_superuser or bool(roles & ROLE_GROUPS.keys())
        user.save()
        user.groups.set(Group.objects.filter(name__in=[ROLE_GROUPS[r] for r in roles if r in ROLE_GROUPS]))
        return user
```

```python
# config/settings.py
AUTHENTICATION_BACKENDS = [
    'users.backends.AuthServiceBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:48000')
AUTH_SERVICE_TIMEOUT = float(os.environ.get('AUTH_SERVICE_TIMEOUT', '3'))
```

Группа `Менеджеры` с правами на модели задач заводится в админке или миграцией с `RunPython`.

### Что здесь важно

**Локальный пользователь всё равно нужен.** Сессии, `LogEntry` (журнал действий в админке), группы и внешние ключи ссылаются на строку в таблице пользователей. Связь с Auth-сервисом держится на `external_id`, а не на email: email может поменяться. Пароль локально не хранится (`set_unusable_password`), поэтому `ModelBackend` такого пользователя никогда не пустит.

**Роли синхронизируются при каждом входе.** Забрали у менеджера роль в Auth-сервисе — при следующем входе у него снимется `is_staff`. Но уже открытая сессия в админке продолжит жить до своего конца: Django спросит у Auth-сервиса только при новом входе. Если это важно, сократите `SESSION_COOKIE_AGE` или проверяйте роль в middleware.

**Два вида отказа обрабатываются по-разному:**

| Что случилось | Что делает бэкенд | Почему |
|---|---|---|
| Auth-сервис ответил 401 | `raise PermissionDenied` | пароль точно неверный — не даём `ModelBackend` пустить по старому локальному паролю |
| Сеть, таймаут, 5xx | лог, сообщение, `return None` | не знаем, верный ли пароль; `ModelBackend` пустит только аварийного локального админа |

**Таймаут обязателен.** У httpx по умолчанию 5 секунд, но если Auth-сервис завис, каждый вход держит воркер Django. С сервером, который принимает соединение и молчит, при `AUTH_SERVICE_TIMEOUT=1` вызов `authenticate` вернул `None` через 1,3 секунды, а в логе осталось `httpx.ReadTimeout: timed out`. Без перехвата `httpx.HTTPError` то же исключение дошло бы до пользователя как 500.

**Аварийный вход.** Если Auth-сервис лёг, а в админку зайти нужно, работает локальный суперпользователь из `createsuperuser` с паролем — `ModelBackend` стоит вторым в списке. Такой учётке дают длинный пароль и логин, которого нет в Auth-сервисе.

### Проверка

Против настоящего Auth-сервиса из примера (`docker compose -p kb-auth up`) вход в `/admin/login/` дал:

```text
admin@example.com  (роль admin)    → 302 /admin/, is_superuser=True
boss@example.com   (роль manager)  → 302 /admin/, is_staff=True, группа «Менеджеры»
anna@example.com   (роль user)     → 200, «Пожалуйста, введите корректные имя пользователя и пароль...»
```

После остановки контейнера Auth-сервиса страница входа отвечает 200 с сообщением «Сервис авторизации недоступен, попробуйте позже», в логе — `httpx.ConnectError: [Errno 61] Connection refused`, ответов 500 нет.

В тестах сеть не нужна: `httpx.MockTransport` принимает функцию, которая по запросу возвращает ответ.

```python
# users/tests.py
def fake_auth_service(request: httpx.Request) -> httpx.Response:
    if request.url.path == '/auth/login':
        data = json.loads(request.content)
        if data['email'] in PROFILES and data['password'] == 'secret123':
            return httpx.Response(200, json={'access_token': data['email'], 'refresh_token': 'r'})
        return httpx.Response(401, json={'detail': 'Неверный email или пароль'})
    if request.url.path == '/auth/me':
        return httpx.Response(200, json=PROFILES[request.headers['Authorization'].removeprefix('Bearer ')])
    return httpx.Response(404)


def service_down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError('Connection refused', request=request)


class AuthServiceBackendTests(TestCase):
    def setUp(self):
        Group.objects.create(name='Менеджеры')
        patcher = patch.object(AuthServiceBackend, 'transport', httpx.MockTransport(fake_auth_service))
        patcher.start()
        self.addCleanup(patcher.stop)

    def admin_login(self, username, password='secret123'):
        return self.client.post('/admin/login/?next=/admin/', {'username': username, 'password': password})

    def test_admin_role_becomes_superuser(self):
        self.assertRedirects(self.admin_login('admin@example.com'), '/admin/')
        user = User.objects.get(external_id=1)
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertFalse(user.has_usable_password())

    def test_service_down_shows_message_and_no_500(self):
        with patch.object(AuthServiceBackend, 'transport', httpx.MockTransport(service_down)):
            with self.assertLogs('users.backends', 'ERROR'):
                response = self.admin_login('admin@example.com')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Сервис авторизации недоступен')
        self.assertNotIn('_auth_user_id', self.client.session)
```

Всего восемь тестов бэкенда: кроме этих, менеджер получает группу, обычный пользователь не входит в админку, снятая роль снимает `is_staff` при следующем входе, отказ Auth-сервиса не даёт войти по локальному паролю, существующий локальный пользователь привязывается без ошибки unique, аварийный админ входит при недоступном сервисе.

Что ждёт бэкенд от ответа `/auth/me` (`id`, `email`, `roles`), записано как [контракт](../../../microservices/contracts.md#контрактные-тесты), и Auth-сервис проверяет его в своих тестах.

## SSO в двух словах

**SSO** (single sign-on, единый вход) — пользователь входит один раз и попадает во все приложения компании без повторного ввода пароля. Пароль при этом вводится только на странице сервера авторизации, а приложения его не видят вовсе: они перенаправляют браузер на сервер, получают обратно одноразовый код и меняют его на токены (OpenID Connect поверх OAuth2). Бэкенд выше — не SSO: пароль вводится в форме Django и проходит через неё. Для настоящего SSO Django подключают к OIDC-серверу вроде [Keycloak](../../../microservices/keycloak/README.md) через `mozilla-django-oidc` или `django-allauth`, а бэкенд из этих библиотек делает то же, что `_sync_user`: создаёт локального пользователя по данным из токена.

## Сессии и CSRF

После входа Django хранит в сессии id пользователя и путь к бэкенду, а браузер получает cookie `sessionid`. По умолчанию сессии лежат в базе (таблица `django_session`); `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'` переносит их в Redis или другой кэш. Выход (`logout`) удаляет сессию на сервере, поэтому отзывается мгновенно, в отличие от JWT.

Раз браузер сам прикладывает cookie к каждому запросу, чужой сайт может отправить форму от имени вошедшего пользователя. От этого защищает `CsrfViewMiddleware`: каждая форма с методом POST несёт токен `csrfmiddlewaretoken` (тег `{% csrf_token %}`), который должен совпасть с cookie `csrftoken`. Если запрос приходит не с того же сайта, Django отвечает 403. Подробнее об атаке и защите — в заметке [Атаки на браузер](../../../web/security/browser_attacks.md).

Полезные настройки для продакшена: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True` (cookie только по HTTPS), `CSRF_TRUSTED_ORIGINS` — если админка открывается с другого домена или за прокси.

## Частые ошибки

- **Начать проект со стандартного `User`.** Через год понадобится вход по email, а переключить `AUTH_USER_MODEL` уже нельзя без ручного переноса. Начинайте с `class User(AbstractUser): pass`.
- **`from django.contrib.auth.models import User` в коде.** После замены модели — `Manager isn't available; 'auth.User' has been swapped`. Используйте `get_user_model()` и `settings.AUTH_USER_MODEL`.
- **HTTP-запрос из бэкенда без таймаута и без перехвата ошибок.** Упавший Auth-сервис превращает страницу входа в 500 или вешает воркеры.
- **Возвращать `None`, когда внешний сервис сказал «неверный пароль».** Следующий `ModelBackend` проверит локальный пароль, и старый пароль, который уже сменили в Auth-сервисе, снова откроет вход. Здесь нужен `PermissionDenied`.
- **Искать локального пользователя по email.** Сменил email в Auth-сервисе — получил вторую учётку. Храните внешний id.
- **Копировать пароль в локальную базу «на всякий случай».** Две копии хэша расходятся, и непонятно, какая главная. Пароль хранит один сервис.
- **Удалить бэкенд из `AUTHENTICATION_BACKENDS`, пока есть сессии, созданные через него.** Эти пользователи окажутся анонимными.

## Когда не использовать

- **Один Django-проект без других сервисов.** Стандартного `ModelBackend` хватает, внешний сервис только добавит точку отказа.
- **Нужен единый вход для нескольких приложений.** Не пересылайте пароли через каждое приложение — подключите OIDC-сервер (см. SSO выше).

## Связанные темы

- [Сессии на JWT: refresh, выход, роли](../../fast_api/docs/auth_sessions.md) — Auth-сервис, через который входит админка
- [Админка](admin.md)
- [Миграции](migrations.md) — почему смена модели пользователя ломает историю
- [Сигналы](signals.md) — создание профиля при регистрации
- [HTTPX](../../../microservices/httpx/README.md) — HTTP-клиент
- [Keycloak](../../../microservices/keycloak/README.md) — OIDC-сервер для SSO
- [Атаки на браузер](../../../web/security/browser_attacks.md) — CSRF и XSS
