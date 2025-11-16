Чтобы использовать шаблоны, необходимо установить пакет Jinja
```sh
pip install jinja2
```
Создадим новую папку `templates`, в каталоге нашего проекта. В этой папке будут храниться все наши файлы Jinja, которые представляют собой файлы HTML. Jinja должен определить эту папку путем создания экземпляра Jinja2Templates в FastAPI.

```python
from fastapi.templating import Jinja2Templates


app = FastAPI()
templates = Jinja2Templates(directory="templates")
```

Пример макета родительского шаблона main.html:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>CRUD Project FastAPI</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
          rel="stylesheet"
          integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN"
          crossorigin="anonymous">
  </head>
  <body>
    <header>
      <nav class="navar">
        <div class="p-3 mb-2 bg-primary text-white">
          <h1>CRUD Application</h1>
        </div>
      </nav>
    </header>
    <div class="container-fluid">
      {% block crud_container %}
      {% endblock %}
    </div>
  </body>
</html>
```

Другие шаблоны могут наследовать структуру и дизайн этого файла `main.html` с помощью тегов `{% extends %}`. Базовый шаблон имеет теги Jinja, а именно теги `{% block crud_container %}` и `{% endblock %}`, которые указывают, куда дочерние шаблоны могут вставлять свой контент.

Пример макета дочернего шаблона `message.html`:

```html
{% extends "main.html" %}

{% block crud_container %}
  {% if message %}
    <article class="card container-fluid">
      <br/>
      <h2>ID: {{ message.id }}</h2>
      <p>
        <strong>Text: {{ message.text }}</strong>
      </p>
    </article>
  {% else %}
    <section class="container-fluid">
      <h2 align="center">Messages</h2>
      <br>
      <div class="card">
        <ul class="list-group list-group-flush">
          {% for message in messages %}
            <li class="list-group-item">
              {{ message.id }}. <a href="/message/{{message.id}}">{{ message.text }}</a>
            </li>
          {% endfor %}
        </ul>
      </div>
    </section>
  {% endif %}
{% endblock %}
```

Он наследуется от базового шаблона, чтобы следовать принципу DRY(не повторяйся) и выводит в цикле наши записи, в виде маркированного списка выводим ID и сам текст записи

Пример рендеринга страницы по шаблону:

```python
from fastapi import FastAPI, status, Body, HTTPException, Request
from fastapi.responses import HTMLResponse


@app.get("/")
async def get_all_messages(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "message.html", {"messages": messages_db})
```