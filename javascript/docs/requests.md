# HTTP-запросы в JavaScript: Fetch и Axios

В браузере запросы обычно выполняют встроенным `fetch()`. Axios решает ту же задачу как сторонняя библиотека и добавляет удобные настройки, interceptors и единообразный формат ошибок. Эта глава показывает практическую работу с обоими вариантами.

## Fetch

`fetch()` — современный встроенный API для выполнения сетевых запросов. Он принимает URL или объект `Request`, необязательные настройки и сразу возвращает `Promise<Response>`:

```js
const promise = fetch(url, options) // отправляем HTTP-запрос и получаем Promise с Response
```

С помощью `options` задают метод, заголовки, тело, режим работы с cookies, сигнал отмены и другие параметры. Сам объект `Response` содержит статус и заголовки, а его тело читается отдельно через асинхронные методы `json()`, `text()`, `blob()` и другие.

### GET и JSON

Для GET-запроса достаточно URL. После получения ответа отдельно проверяют статус и асинхронно читают JSON-тело.

```js
async function getPosts() { // объявляем асинхронную функцию, которая возвращает Promise
  const response = await fetch('https://example.com/api/posts') // ожидаем завершения асинхронной операции и сохраняем результат

  if (!response.ok) { // проверяем условие и выполняем блок, если оно истинно
    throw new Error(`Ошибка запроса: ${response.status}`) // создаём ошибку и передаём её вызывающему коду
  }

  return await response.json() // возвращаем вызывающему коду значение выражения await response.json()
}
```

`response.json()` асинхронно читает тело ответа и преобразует JSON в значение JavaScript.

`fetch()` не создаёт исключение для статусов `404` или `500`, поэтому `response.ok` нужно проверять вручную. Это свойство равно `true` для статусов от `200` до `299`.

Тот же запрос можно записать цепочкой Promise без `async/await`:

```js
fetch('https://example.com/api/posts') // отправляем HTTP-запрос и получаем Promise с Response
  .then((response) => { // обрабатываем успешный результат Promise
    if (!response.ok) { // проверяем условие и выполняем блок, если оно истинно
      throw new Error(`Ошибка запроса: ${response.status}`) // создаём ошибку и передаём её вызывающему коду
    }

    return response.json() // возвращаем вызывающему коду значение выражения response.json()
  })
  .then((posts) => console.log(posts)) // обрабатываем успешный результат Promise
  .catch((error) => console.error(error)) // обрабатываем ошибку Promise
```

`async/await` не меняет работу `fetch`, а только делает последовательную работу с Promise более похожей на обычный код.

### Ошибки Fetch

Fetch различает сетевую ошибку и неуспешный HTTP-статус: первая отклоняет Promise, а второй нужно проверить через `response.ok`.

```js
try { // начинаем блок, в котором может возникнуть ошибка
  const posts = await getPosts() // ожидаем завершения асинхронной операции и сохраняем результат
  console.log(posts) // выводим значение в консоль
} catch (error) { // перехватываем возникшую ошибку
  console.error(error.message) // выводим ошибку в консоль
}
```

В `catch` попадают сетевые ошибки, отмена запроса, ошибки чтения ответа и исключения, созданные через `throw`.

### Query-параметры

Для адреса `/api/posts?limit=10&offset=20` параметры удобно собрать через `URL`:

```js
const url = new URL('/api/posts', 'https://example.com') // создаём новый экземпляр и сохраняем его в переменной
url.searchParams.set('limit', String(10)) // сохраняем значение в коллекции
url.searchParams.set('offset', String(20)) // сохраняем значение в коллекции

const response = await fetch(url) // ожидаем завершения асинхронной операции и сохраняем результат
```

### POST с JSON

При отправке объекта его превращают в JSON-строку и сообщают серверу формат тела заголовком `Content-Type`.

```js
async function createPost(post) { // объявляем асинхронную функцию, которая возвращает Promise
  const response = await fetch('https://example.com/api/posts', { // ожидаем завершения асинхронной операции и сохраняем результат
    method: 'POST', // задаём свойство method
    headers: { // задаём свойство headers
      'Content-Type': 'application/json', // задаём свойство Content-Type
    },
    body: JSON.stringify(post), // преобразуем значение JavaScript в строку JSON
  })

  if (!response.ok) { // проверяем условие и выполняем блок, если оно истинно
    throw new Error(`Ошибка создания: ${response.status}`) // создаём ошибку и передаём её вызывающему коду
  }

  return await response.json() // возвращаем вызывающему коду значение выражения await response.json()
}
```

`JSON.stringify()` превращает объект JavaScript в строку JSON. Заголовок `Content-Type` сообщает серверу формат тела.

### PATCH и DELETE

PATCH обычно передаёт только изменяемые поля, а DELETE удаляет ресурс по его адресу. Конкретный формат ответа определяет API сервера.

```js
async function updatePost(postId, changes) { // объявляем асинхронную функцию, которая возвращает Promise
  const response = await fetch(`/api/posts/${postId}`, { // ожидаем завершения асинхронной операции и сохраняем результат
    method: 'PATCH', // задаём свойство method
    headers: { // задаём свойство headers
      'Content-Type': 'application/json', // задаём свойство Content-Type
    },
    body: JSON.stringify(changes), // преобразуем значение JavaScript в строку JSON
  })

  if (!response.ok) { // проверяем условие и выполняем блок, если оно истинно
    throw new Error(`Ошибка обновления: ${response.status}`) // создаём ошибку и передаём её вызывающему коду
  }

  return await response.json() // возвращаем вызывающему коду значение выражения await response.json()
}

async function deletePost(postId) { // объявляем асинхронную функцию, которая возвращает Promise
  const response = await fetch(`/api/posts/${postId}`, { // ожидаем завершения асинхронной операции и сохраняем результат
    method: 'DELETE', // задаём свойство method
  })

  if (!response.ok) { // проверяем условие и выполняем блок, если оно истинно
    throw new Error(`Ошибка удаления: ${response.status}`) // создаём ошибку и передаём её вызывающему коду
  }
}
```

Успешный `DELETE` часто возвращает `204 No Content`. У такого ответа нет тела, поэтому `response.json()` вызывать не нужно.

### Заголовок авторизации

При авторизации по access token его обычно передают в заголовке `Authorization`, а не в URL:

```js
const response = await fetch('/api/profile', { // ожидаем завершения асинхронной операции и сохраняем результат
  headers: { // задаём свойство headers
    Authorization: `Bearer ${accessToken}`, // задаём свойство Authorization
  },
})
```

Схему `Bearer` и формат токена определяет API. Не добавляйте слово `Bearer`, если сервер ожидает другую схему.

Если сервер использует cookie-сессию, для cross-origin запроса может понадобиться параметр `credentials`:

```js
const response = await fetch('https://api.example.com/profile', { // ожидаем завершения асинхронной операции и сохраняем результат
  credentials: 'include', // задаём свойство credentials
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
const formData = new FormData() // создаём новый экземпляр и сохраняем его в переменной
formData.append('image', file) // добавляем узлы или текст в конец элемента

await fetch('/api/images', { // отправляем HTTP-запрос и получаем Promise с Response
  method: 'POST', // задаём свойство method
  body: formData, // задаём свойство body
})
```

Для `FormData` не задавайте `Content-Type` вручную. Браузер сам добавит `multipart/form-data` с правильной границей.

### Отмена запроса

`AbortController` создаёт сигнал отмены. Один и тот же сигнал можно передать операции, а затем вызвать `abort()`, когда её результат больше не нужен.

```js
const controller = new AbortController() // создаём новый экземпляр и сохраняем его в переменной

try { // начинаем блок, в котором может возникнуть ошибка
  const response = await fetch('/api/posts', { // ожидаем завершения асинхронной операции и сохраняем результат
    signal: controller.signal, // задаём свойство signal
  })
} catch (error) { // перехватываем возникшую ошибку
  if (error.name !== 'AbortError') { // проверяем условие и выполняем блок, если оно истинно
    console.error(error) // выводим ошибку в консоль
  }
}

controller.abort() // отменяем операции, использующие signal этого контроллера
```

После `abort()` Promise отклоняется с ошибкой `AbortError`.

### `fetch` и `XMLHttpRequest`

`XMLHttpRequest` — более старый браузерный API для HTTP-запросов, основанный на событиях и callbacks. `fetch` основан на Promise, естественно работает с `async/await`, использует объекты `Request`, `Response`, `Headers` и поддерживает потоковое чтение ответа.

```js
const request = new XMLHttpRequest() // создаём новый экземпляр и сохраняем его в переменной
request.open('GET', '/api/posts') // вызываем request.open()

request.addEventListener('load', () => { // подписываемся на событие
  console.log(request.responseText) // выводим значение в консоль
})

request.addEventListener('error', () => { // подписываемся на событие
  console.error('Сетевая ошибка') // выводим ошибку в консоль
})

request.send() // вызываем request.send()
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
import axios from 'axios' // импортируем значение из другого модуля

const response = await axios.get('https://example.com/api/posts', { // ожидаем завершения асинхронной операции и сохраняем результат
  params: { // задаём свойство params
    limit: 10, // задаём свойство limit
    offset: 20, // задаём свойство offset
  },
})

console.log(response.data) // выводим значение в консоль
```

Axios самостоятельно преобразует JSON. Готовые данные находятся в `response.data`.

### POST, PATCH и DELETE

Для методов с телом Axios принимает JavaScript-объект и самостоятельно сериализует его в JSON.

```js
const createdPost = await axios.post('/api/posts', { // ожидаем завершения асинхронной операции и сохраняем результат
  title: 'Новый пост', // задаём свойство title
  content: 'Содержимое', // задаём свойство content
})

const updatedPost = await axios.patch('/api/posts/post-id', { // ожидаем завершения асинхронной операции и сохраняем результат
  title: 'Изменённый заголовок', // задаём свойство title
})

await axios.delete('/api/posts/post-id') // отправляем DELETE-запрос для указанного поста
```

### Общий экземпляр

Если запросы используют один базовый адрес и общие настройки, создают настроенный экземпляр Axios и импортируют его в API-модули.

```js
import axios from 'axios' // импортируем значение из другого модуля

export const apiClient = axios.create({ // экспортируем значение из модуля
  baseURL: 'https://example.com/api', // задаём свойство baseURL
  timeout: 5000, // задаём свойство timeout
  headers: { // задаём свойство headers
    Accept: 'application/json', // задаём свойство Accept
  },
})
```

Общий экземпляр хранит базовый адрес, таймаут и заголовки в одном месте.

### Ошибки Axios

Axios создаёт исключение для неуспешных HTTP-статусов:

```js
import axios from 'axios' // импортируем значение из другого модуля

try { // начинаем блок, в котором может возникнуть ошибка
  const response = await axios.get('/api/posts') // ожидаем завершения асинхронной операции и сохраняем результат
  console.log(response.data) // выводим значение в консоль
} catch (error) { // перехватываем возникшую ошибку
  if (axios.isAxiosError(error)) { // проверяем условие и выполняем блок, если оно истинно
    console.log(error.response?.status) // выводим значение в консоль
    console.log(error.response?.data) // выводим значение в консоль
    console.log(error.message) // выводим значение в консоль
  } else { // выполняем ветку, когда предыдущие условия ложны
    throw error // создаём ошибку и передаём её вызывающему коду
  }
}
```

- `error.response` содержит ответ сервера;
- `error.request` существует, если запрос отправлен, но ответ не получен;
- `error.message` содержит общее сообщение.

### Interceptors

Interceptor выполняет общую логику перед запросом или после ответа:

```js
apiClient.interceptors.request.use((config) => { // вызываем apiClient.interceptors.request.use()
  const token = localStorage.getItem('accessToken') // читаем access token из localStorage

  if (token) { // проверяем условие и выполняем блок, если оно истинно
    config.headers.Authorization = `Bearer ${token}` // записываем `Bearer ${token}` в свойство Authorization
  }

  return config // возвращаем вызывающему коду значение выражения config
})
```

Interceptors используют для авторизации и общей обработки ошибок, но не для логики одной конкретной страницы.

### Отмена Axios-запроса

Современный Axios принимает стандартный `AbortSignal`, поэтому запрос отменяется тем же `AbortController`, что и Fetch.

```js
const controller = new AbortController() // создаём новый экземпляр и сохраняем его в переменной

axios.get('/api/posts', { // запускаем GET-запрос и передаём стандартный сигнал отмены
  signal: controller.signal, // задаём свойство signal
})

controller.abort() // отменяем операции, использующие signal этого контроллера
```

Для нового кода используется стандартный `AbortController`. Старый API `CancelToken` устарел
