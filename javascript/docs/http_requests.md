# HTTP-запросы в JavaScript: Fetch и Axios

## Как устроен HTTP-запрос

Клиент отправляет серверу URL, HTTP-метод, заголовки и иногда тело запроса. Сервер возвращает статус, заголовки и данные.

Основные методы:

- `GET` — получить данные;
- `POST` — создать запись;
- `PUT` — полностью заменить запись;
- `PATCH` — частично изменить запись;
- `DELETE` — удалить запись.

Группы статусов:

- `2xx` — успешный запрос;
- `4xx` — ошибка запроса клиента;
- `5xx` — ошибка сервера.

Подробнее о протоколе: [HTTP](../../web/http/README.md).

## Fetch

`fetch()` — встроенная функция браузера, возвращающая `Promise` с объектом `Response`.

### GET и JSON

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

### Обработка ошибок

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

```js
const response = await fetch('/api/profile', {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
})
```

### Отправка файлов

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

### Параллельные запросы

```js
const [postsResponse, usersResponse] = await Promise.all([
  fetch('/api/posts'),
  fetch('/api/users'),
])

const [posts, users] = await Promise.all([
  postsResponse.json(),
  usersResponse.json(),
])
```

Если один запрос зависит от результата другого, их выполняют последовательно.

## Axios

Axios — сторонняя библиотека для HTTP-запросов:

```sh
npm install axios
```

### GET и query-параметры

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

### Обработка ошибок

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

```js
const controller = new AbortController()

axios.get('/api/posts', {
  signal: controller.signal,
})

controller.abort()
```

Для нового кода используется стандартный `AbortController`. Старый API `CancelToken` устарел