"""Шаблоны, которые пишут менеджеры в админке: песочница и проверка до сохранения."""

from jinja2 import StrictUndefined, TemplateSyntaxError, UndefinedError, meta
from jinja2.exceptions import SecurityError
from jinja2.sandbox import SandboxedEnvironment

env = SandboxedEnvironment(autoescape=True, undefined=StrictUndefined)

ALLOWED_VARIABLES = {'user_name', 'task_title', 'task_url', 'due_date'}
SAMPLE_CONTEXT = {
    'user_name': 'Анна',
    'task_title': 'Сдать отчёт',
    'task_url': 'https://tasker.test/tasks/42',
    'due_date': '31 октября',
}


def validate(source: str) -> str:
    """Возвращает пробный рендер или бросает ValueError с понятным текстом."""
    try:
        ast = env.parse(source)
    except TemplateSyntaxError as error:
        raise ValueError(f'синтаксис, строка {error.lineno}: {error.message}') from None
    unknown = meta.find_undeclared_variables(ast) - ALLOWED_VARIABLES
    if unknown:
        raise ValueError(f'неизвестные переменные: {", ".join(sorted(unknown))}')
    try:
        return env.from_string(source).render(SAMPLE_CONTEXT)
    except (SecurityError, UndefinedError) as error:
        raise ValueError(f'{type(error).__name__}: {error}') from None


drafts = {
    'нормальный': '{{ user_name }}, задача «{{ task_title }}» ждёт вас до {{ due_date }}.',
    'опечатка в теге': '{{ user_name }}, {% if task_title %}задача ждёт{% endfi %}',
    'опечатка в переменной': '{{ username }}, задача «{{ task_title }}»',
    'чужие данные': '{{ user_name }}, ваш пароль: {{ user.password_hash }}',
}
for name, source in drafts.items():
    try:
        print(f'{name}: OK → {validate(source)}')
    except ValueError as error:
        print(f'{name}: отклонён → {error}')

print('\nПопытки выбраться из песочницы (рендер с разрешёнными переменными):')
attacks = [
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    '{{ task_title.__class__.__base__ }}',
    "{{ task_title.format.__globals__ }}",
    "{{ (task_title|attr('__class__')).__mro__ }}",
    '{{ range(10 ** 9) | list | length }}',
]
for source in attacks:
    try:
        env.from_string(source).render(SAMPLE_CONTEXT)
        print('  ПРОШЛО:', source)
    except SecurityError as error:
        print(f'  SecurityError: {error}')
    except OverflowError as error:
        print(f'  OverflowError: {error}')

print('\nТот же трюк в обычном Environment:')
from jinja2 import Environment  # noqa: E402

leaked = Environment().from_string("{{ ''.__class__.__mro__[1].__subclasses__() | length }}").render()
print('  доступно классов интерпретатора:', leaked)
