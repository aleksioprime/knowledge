Чтобы использовать формы, необходимо установить `python-multipart`:
```sh
pip install python-multipart
```

Чтобы принять текст записи из формы, мы должны установить `Form()` к параметру, который мы будем принимать из формы. В нашем случае это сам текст записи. Мы можем настроить `Form` точно так же, как и  `Body`, `Query`, `Path`, включая параметры валидации, описания и тд.

Пример шаблона с формой:
```html
<section class="container-fluid">
  <form method="post" action="/">
    <div class="col-auto">
      <div class="input-group mb-3">
        <input type="text" name="message" class="form-control"
               placeholder="Add new message" aria-label="Add message"
               aria-describedby="button-addon2"/>
        <button class="btn btn-outline-primary" type="submit" id="button-addon2"
                data-mdb-ripple-color="dark">Add
        </button>
      </div>
     </div>
  </form>
</section>
```

Пример API:
```python
from fastapi import FastAPI, status, Body, HTTPException, Request, Form


@app.post("/", status_code=status.HTTP_201_CREATED)
async def create_message(request: Request, message: str = Form()) -> HTMLResponse:
    if messages_db:
        max_id_message = max(messages_db, key=lambda m: m.id).id + 1
    else:
        max_id_message = 0
    messages_db.append(Message(id=max_id_message, text=message))
    return templates.TemplateResponse(request, "message.html", {"messages": messages_db})
```