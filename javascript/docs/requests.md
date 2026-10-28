# HTTP-запросы в JavaScript: Fetch и Axios

В браузере запросы обычно выполняют встроенным `fetch()`. Axios решает ту же задачу как сторонняя библиотека и добавляет удобные настройки, interceptors и единообразный формат ошибок. Эта глава показывает практическую работу с обоими вариантами.

## Fetch

`fetch()` — современный встроенный API для выполнения сетевых запросов. Он принимает URL или объект `Request`, необязательные настройки и сразу возвращает `Promise<Response>`:

```js
const promise = fetch(url, options)
```

С помощью `options` задают метод, заголовки, тело, режим работы с cookies, сигнал отмены и другие параметры. Сам объект `Response` содержит статус и заголовки, а его тело читается отдельно через асинхронные методы `json()`, `text()`, `blob()` и другие.

### GET и JSON

Для GET-запроса достаточно URL. После получения ответа отдельно проверяют статус и асинхронно читают JSON-тело.

```js
async function getPosts() {
  const response = await fetch('https://example.com/api/posts')

  if (!response.ok) {
    throw new Error(`Ошибка запроса: ${response.status}`)
  }

  return await response.json()
}
```

`response.json()` асинхронно читает тело ответа и преобразует JSON в значение JavaScript.

`fetch()` не создаёт исключение для статусов `404` или `500`, поэтому `response.ok` нужно проверять вручную. Это свойство равно `true` для статусов от `200` до `299`.

Тот же запрос можно записать цепочкой Promise без `async/await`:

```js
fetch('https://example.com/api/posts')
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Ошибка запроса: ${response.status}`)
    }

    return response.json()
  })
  .then((posts) => console.log(posts))
  .catch((error) => console.error(error))
```

`async/await` не меняет работу `fetch`, а только делает последовательную работу с Promise более похожей на обычный код.

### Ошибки Fetch

Fetch различает сетевую ошибку и неуспешный HTTP-статус: первая отклоняет Promise, а второй нужно проверить через `response.ok`.

```js
try {
  const posts = await getPosts()
  console.log(posts)
} catch (error) {
  console.error(error.message)
}
```

В `catch` попадают сетевые ошибки, отмена запроса, ошибки чтения ответа и исключения, созданные через `throw`.

### Query-параметры

Для адреса `/api/posts?limit=10&offset=20` параметры удобно собрать через `URL`:

```js
const url = new URL('/api/posts', 'https://example.com')
url.searchParams.set('limit', String(10))
url.searchParams.set('offset', String(20))

const response = await fetch(url)
```

### POST с JSON

При отправке объекта его превращают в JSON-строку и сообщают серверу формат тела заголовком `Content-Type`.

```js
async function createPost(post) {
  const response = await fetch('https://example.com/api/posts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(post),
  })

  if (!response.ok) {
    throw new Error(`Ошибка создания: ${response.status}`)
  }

  return await response.json()
}
```

`JSON.stringify()` превращает объект JavaScript в строку JSON. Заголовок `Content-Type` сообщает серверу формат тела.

### PATCH и DELETE

PATCH обычно передаёт только изменяемые поля, а DELETE удаляет ресурс по его адресу. Конкретный формат ответа определяет API сервера.

```js
async function updatePost(postId, changes) {
  const response = await fetch(`/api/posts/${postId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(changes),
  })

  if (!response.ok) {
    throw new Error(`Ошибка обновления: ${response.status}`)
  }

  return await response.json()
}

async function deletePost(postId) {
  const response = await fetch(`/api/posts/${postId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`Ошибка удаления: ${response.status}`)
  }
}
```

Успешный `DELETE` часто возвращает `204 No Content`. У такого ответа нет тела, поэтому `response.json()` вызывать не нужно.

### Заголовок авторизации

При авторизации по access token его обычно передают в заголовке `Authorization`, а не в URL:

```js
const response = await fetch('/api/profile', {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
})
```

Схему `Bearer` и формат токена определяет API. Не добавляйте слово `Bearer`, если сервер ожидает другую схему.

Если сервер использует cookie-сессию, для cross-origin запроса может понадобиться параметр `credentials`:

```js
const response = await fetch('https://api.example.com/profile', {
  credentials: 'include',
})
```

При этом сервер должен явно разрешить credentials и конкретный origin через CORS. Нельзя использовать `Access-Control-Allow-Origin: *` вместе с credentialed-запросом.

Не помещайте секретные токены в query-параметры: URL может попасть в историю, логи и аналитику. Способ хранения токена зависит от архитектуры и модели угроз приложения; защита от XSS и CSRF рассматривается отдельно.

### CORS

Same-origin policy ограничивает чтение ответов от другого origin. Origin образуют схема, домен и порт, поэтому `https://app.example.com` и `https://api.example.com` — разные origin.

CORS — протокол на основе HTTP-заголовков, с помощью которого сервер разрешает браузерному JavaScript читать cross-origin ответ. Например:

```http
Access-Control-Allow-Origin: https://app.example.com
```

Для некоторых запросов браузер сначала автоматически отправляет preflight-запрос методом `OPTIONS`. Он проверяет, разрешены ли origin, метод и нестандартные заголовки. Например, preflight обычно потребуется для `PATCH` или заголовка `Authorization`.

CORS настраивается на сервере. Добавление заголовка `Access-Control-Allow-Origin` в клиентский `fetch` не поможет. Режим `mode: 'no-cors'` тоже не является обходом: JavaScript получает непрозрачный ответ и не может прочитать его статус или тело.

### Отправка файлов

Файлы и обычные поля формы объединяют в объект `FormData`, который браузер преобразует в тело `multipart/form-data`.

```js
const formData = new FormData()
formData.append('image', file)

await fetch('/api/images', {
  method: 'POST',
  body: formData,
})
```

Для `FormData` не задавайте `Content-Type` вручную. Браузер сам добавит `multipart/form-data` с правильной границей.

### Отмена запроса

`AbortController` создаёт сигнал отмены. Один и тот же сигнал можно передать операции, а затем вызвать `abort()`, когда её результат больше не нужен.

```js
const controller = new AbortController()

try {
  const response = await fetch('/api/posts', {
    signal: controller.signal,
  })
} catch (error) {
  if (error.name !== 'AbortError') {
    console.error(error)
  }
}

controller.abort()
```

После `abort()` Promise отклоняется с ошибкой `AbortError`.

### `fetch` и `XMLHttpRequest`

`XMLHttpRequest` — более старый браузерный API для HTTP-запросов, основанный на событиях и callbacks. `fetch` основан на Promise, естественно работает с `async/await`, использует объекты `Request`, `Response`, `Headers` и поддерживает потоковое чтение ответа.

```js
const request = new XMLHttpRequest()
request.open('GET', '/api/posts')

request.addEventListener('load', () => {
  console.log(request.responseText)
})

request.addEventListener('error', () => {
  console.error('Сетевая ошибка')
})

request.send()
```

Для нового кода обычно выбирают `fetch`. `XMLHttpRequest` всё ещё встречается в старых проектах и имеет встроенные события прогресса загрузки и отправки данных. CORS и same-origin policy применяются к обоим API.

## Axios

Axios — сторонняя библиотека для HTTP-запросов:

```sh
npm install axios
```

### GET и query-параметры

Axios возвращает объект ответа, а готовые данные помещает в `response.data`. Query-параметры удобнее передавать отдельным объектом `params`.

```js
import axios from 'axios'

const response = await axios.get('https://example.com/api/posts', {
  params: {
    limit: 10,
    offset: 20,
  },
})

console.log(response.data)
```

Axios самостоятельно преобразует JSON. Готовые данные находятся в `response.data`.

### POST, PATCH и DELETE

Для методов с телом Axios принимает JavaScript-объект и самостоятельно сериализует его в JSON.

```js
const createdPost = await axios.post('/api/posts', {
  title: 'Новый пост',
  content: 'Содержимое',
})

const updatedPost = await axios.patch('/api/posts/post-id', {
  title: 'Изменённый заголовок',
})

await axios.delete('/api/posts/post-id')
```

### Общий экземпляр

Если запросы используют один базовый адрес и общие настройки, создают настроенный экземпляр Axios и импортируют его в API-модули.

```js
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: 'https://example.com/api',
  timeout: 5000,
  headers: {
    Accept: 'application/json',
  },
})
```

Общий экземпляр хранит базовый адрес, таймаут и заголовки в одном месте.

### Ошибки Axios

Axios создаёт исключение для неуспешных HTTP-статусов:

```js
import axios from 'axios'

try {
  const response = await axios.get('/api/posts')
  console.log(response.data)
} catch (error) {
  if (axios.isAxiosError(error)) {
    console.log(error.response?.status)
    console.log(error.response?.data)
    console.log(error.message)
  } else {
    throw error
  }
}
```

- `error.response` содержит ответ сервера;
- `error.request` существует, если запрос отправлен, но ответ не получен;
- `error.message` содержит общее сообщение.

### Interceptors

Interceptor выполняет общую логику перед запросом или после ответа:

```js
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})
```

Interceptors используют для авторизации и общей обработки ошибок, но не для логики одной конкретной страницы.

### Отмена Axios-запроса

Современный Axios принимает стандартный `AbortSignal`, поэтому запрос отменяется тем же `AbortController`, что и Fetch.

```js
const controller = new AbortController()

axios.get('/api/posts', {
  signal: controller.signal,
})

controller.abort()
```

Для нового кода используется стандартный `AbortController`. Старый API `CancelToken` устарел
