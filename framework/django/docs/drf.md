# Django REST Framework

Django из коробки отдаёт HTML-страницы, а фронтенду и мобильному приложению нужен JSON. Django REST Framework (DRF) добавляет к Django всё для API: сериализаторы (превращают модели в JSON и проверяют входные данные), классы представлений, роутеры, аутентификацию, права и пагинацию. Тот же API задач, что в [«Задачнике»](../../../pet/tasker/README.md) на FastAPI, здесь занимает около 60 строк.

```bash
pip install djangorestframework
```

## Минимальный пример

```python
# tasks/serializers.py
from rest_framework import serializers

from .models import Tag, Task


class TaskSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    tags = serializers.SlugRelatedField(many=True, slug_field='name', queryset=Tag.objects.all(), required=False)

    class Meta:
        model = Task
        fields = ['id', 'title', 'done', 'priority', 'due_date', 'tags', 'owner', 'created_at']
        read_only_fields = ['created_at']
```

```python
# tasks/views.py
from rest_framework import viewsets


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        # Только свои задачи: чужие для пользователя просто не существуют (404)
        return Task.objects.filter(owner=self.request.user).select_related('owner').prefetch_related('tags')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
```

```python
# tasks/urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='task')
urlpatterns = router.urls
```

```bash
curl -u anna:secret123 -X POST localhost:8000/api/tasks/ -H 'Content-Type: application/json' \
  -d '{"title": "Записаться к врачу", "tags": ["дом"]}'
# {"id":4,"title":"Записаться к врачу","done":false,"priority":1,"due_date":null,"tags":["дом"],"owner":"anna","created_at":"..."}

curl -u anna:secret123 localhost:8000/api/tasks/
# {"count":3,"next":null,"previous":null,"results":[...]}
```

## Как это работает

**Сериализатор** делает две работы: превращает объект модели в словарь для JSON и проверяет входящие данные. `ModelSerializer` берёт поля и проверки из модели — длину `title`, валидаторы `priority`:

```json
{
  "title": ["Это поле не может быть пустым."],
  "priority": ["Убедитесь, что это значение меньше либо равно 5."],
  "tags": ["Объект с name=нет-такой не существует."]
}
```

Ответ на неверные данные — `400 Bad Request` со списком ошибок по полям.

**`ModelViewSet`** — один класс на все действия: список, создание, получение, полное и частичное изменение, удаление. **Роутер** сам строит адреса: `/api/tasks/` и `/api/tasks/{id}/`.

- `get_queryset` определяет, какие объекты вообще доступны. Фильтр по владельцу делает чужие задачи недоступными: на `GET /api/tasks/3/` придёт 404, как и в «Задачнике».
- `perform_create` подставляет владельца, чтобы клиент не мог создать задачу от чужого имени.

**Свои действия** добавляет декоратор `@action`:

```python
from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response


@action(detail=False)
def stats(self, request):
    stats = Task.objects.filter(owner=request.user).aggregate(
        total=Count('id'), done=Count('id', filter=Q(done=True))
    )
    return Response(stats)

# GET /api/tasks/stats/ → {"total":3,"done":1}
```

**Общие настройки** — в `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

Если открыть `/api/tasks/` в браузере, DRF покажет **Browsable API** — страницу, где можно войти и отправлять запросы формой. Удобно для разработки.

## Тесты

```python
# tasks/tests.py
from rest_framework.test import APITestCase


class TaskApiTests(APITestCase):
    def setUp(self):
        self.anna = User.objects.create_user('anna', password='secret123')
        self.client.force_authenticate(self.anna)

    def test_foreign_task_is_hidden(self):
        task = Task.objects.create(title='Личное', owner=User.objects.create_user('boris'))
        response = self.client.get(f'/api/tasks/{task.id}/')
        self.assertEqual(response.status_code, 404)
```

`python manage.py test` создаёт отдельную тестовую базу, а каждый тест выполняется в транзакции, которая потом откатывается. Чистить данные вручную не нужно.

## DRF или FastAPI

| | Django + DRF | FastAPI |
|---|---|---|
| Что в комплекте | ORM, миграции, админка, пользователи, права | только API; база, миграции, авторизация — отдельными библиотеками |
| Описание данных | сериализаторы | модели Pydantic на подсказках типов |
| Асинхронность | частичная: Django умеет async, но ORM и DRF в основном синхронные | асинхронный изначально |
| Документация API | через `drf-spectacular` | OpenAPI и `/docs` сразу |
| Когда выбирать | продукт с админкой, пользователями, большой бизнес-логикой и командой, которой нужны общие договорённости | API и микросервисы, много ввода-вывода, когда хочется собрать стек самому |

Оба варианта решают одну задачу. Сравните [«Задачник» на FastAPI](../../../pet/tasker/README.md) и [пример на Django](../example/README.md): у FastAPI больше кода «склейки» (сессия, JWT, обработчики ошибок), у Django больше готового, но и больше правил, которые нужно знать.

## Частые ошибки

- **`queryset = Task.objects.all()` без фильтра по пользователю.** Любой вошедший пользователь увидит и изменит чужие задачи. Ограничивайте выборку в `get_queryset`.
- **Владелец из тела запроса.** Если `owner` — обычное поле сериализатора, клиент пришлёт чужой id. Делайте его только для чтения и задавайте в `perform_create`.
- **N+1 в сериализаторе.** `ReadOnlyField(source='owner.username')` или вложенный сериализатор обращаются к связи у каждого объекта. В примере это сразу дало 10 лишних запросов. Всегда добавляйте `select_related` и `prefetch_related` в `get_queryset`.
- **403 вместо 401 без авторизации.** Если первым в `DEFAULT_AUTHENTICATION_CLASSES` стоит `SessionAuthentication`, DRF отвечает `403` даже на запрос без учётных данных. Если первым поставить класс, который умеет заголовок `WWW-Authenticate` (Basic, Token), ответ будет `401`.
- **Basic-аутентификация в продакшене.** Логин и пароль идут с каждым запросом. Для API используют токены (`rest_framework.authtoken`, `djangorestframework-simplejwt`) или внешнюю авторизацию вроде [Keycloak](../../../microservices/keycloak/README.md).

## Связанные темы

- [ORM](orm.md)
- [Структура проекта](project.md)
- [FastAPI](../../fast_api/README.md)
- [Авторизация по JWT](../../fast_api/docs/auth_jwt.md)
