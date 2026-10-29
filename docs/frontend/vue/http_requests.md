# HTTP-запросы во Vue

Список задач приходит с сервера, и пока он грузится, пользователь видит пустой экран, а при ошибке сети — ничего. Компоненту нужно не только получить данные, но и показать загрузку, ошибку и не выполнять лишние запросы. Здесь — как связать `fetch` с реактивным состоянием, куда выносить код запросов и как отменять запросы, которые больше не нужны.

Базовая работа с HTTP, `fetch`, Axios, JSON, статусами и CORS описана в разделе [HTTP-запросы в JavaScript](../../languages/javascript/requests.md).

## Минимальный пример

```vue
<script setup>
import { ref } from 'vue'

const tasks = ref([])
const error = ref('')

async function loadTasks() {
  try {
    const response = await fetch('/api/tasks')
    if (!response.ok) throw new Error(`Ошибка запроса: ${response.status}`)
    tasks.value = await response.json()  // [{ id: 1, title: 'Купить хлеб' }, ...]
  } catch (requestError) {
    error.value = requestError.message  // например, «Ошибка запроса: 500»
  }
}

loadTasks()
</script>

<template>
  <p v-if="error">{{ error }}</p>
  <ul v-else>
    <li v-for="task in tasks" :key="task.id">{{ task.title }}</li>
  </ul>
</template>
```

## Как это работает

Здесь рассматривается только интеграция запросов с Vue-приложением.

### Реактивное состояние запроса

Компоненту обычно нужны три значения:

- данные;
- флаг загрузки;
- сообщение об ошибке.

```vue
<script setup>
import { ref } from 'vue'

const posts = ref([])
const isLoading = ref(false)
const error = ref('')

async function loadPosts() {
  isLoading.value = true
  error.value = ''

  try {
    const response = await fetch('https://example.com/api/posts')

    if (!response.ok) {
      throw new Error(`Ошибка запроса: ${response.status}`)
    }

    posts.value = await response.json()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    isLoading.value = false
  }
}

loadPosts()
</script>

<template>
  <p v-if="isLoading">Загрузка...</p>
  <p v-else-if="error">{{ error }}</p>
  <PostsList v-else :posts="posts" />
</template>
```

`finally` выполняется и после успеха, и после ошибки, поэтому подходит для выключения загрузки.

Обычный HTTP-запрос можно запустить прямо в `<script setup>`. `onMounted()` нужен, если запрос зависит от DOM или должен выполняться именно после монтирования компонента.

### API-модули

Не размещайте одинаковый код запросов в разных компонентах. Вынесите HTTP-логику в `src/api`:

```js
// src/api/posts.js
const API_URL = import.meta.env.VITE_API_URL

export async function getPosts(limit = 10, offset = 0) {
  const url = new URL('/api/posts', API_URL)
  url.searchParams.set('limit', String(limit))
  url.searchParams.set('offset', String(offset))

  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Не удалось загрузить посты: ${response.status}`)
  }

  return await response.json()
}
```

Компонент использует готовую функцию:

```vue
<script setup>
import { ref } from 'vue'
import { getPosts } from '@/api/posts'

const posts = ref([])

async function loadPosts() {
  const response = await getPosts(10, 0)
  posts.value = response.items
}
</script>
```

API-модуль отвечает за адреса, параметры и обработку HTTP-статусов. Компонент отвечает за отображение.

### Запросы в Pinia

Если данные используются несколькими компонентами или страницами, состояние и вызов API можно перенести в Pinia:

```js
// src/stores/postStore.js
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getPosts } from '@/api/posts'

export const usePostStore = defineStore('posts', () => {
  const posts = ref([])
  const isLoading = ref(false)
  const error = ref('')

  async function loadPosts() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const response = await getPosts()
      posts.value = response.items
    } catch (requestError) {
      error.value = requestError.message
    } finally {
      isLoading.value = false
    }
  }

  return { posts, isLoading, error, loadPosts }
})
```

Подробнее: [Pinia](pinia.md).

### Отмена при удалении компонента

Долгий запрос можно отменить, когда компонент удаляется:

```vue
<script setup>
import { onUnmounted } from 'vue'

const controller = new AbortController()

async function loadPosts() {
  await fetch('/api/posts', {
    signal: controller.signal,
  })
}

onUnmounted(() => {
  controller.abort()
})
</script>
```

Это предотвращает ненужную работу после ухода со страницы.

### Запрос при изменении значения

Для поиска или фильтра запрос можно связать с `watch()`:

```vue
<script setup>
import { ref, watch } from 'vue'

const query = ref('')
const results = ref([])

watch(query, async (newQuery, _, onCleanup) => {
  const controller = new AbortController()

  onCleanup(() => controller.abort())

  const url = new URL('/api/search', 'https://example.com')
  url.searchParams.set('query', newQuery)

  try {
    const response = await fetch(url, {
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`Ошибка поиска: ${response.status}`)
    }

    results.value = await response.json()
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error(error)
    }
  }
})
</script>
```

Когда `query` изменится снова, Vue вызовет cleanup и отменит предыдущий запрос. Для текстового поиска также часто добавляют debounce.

### Переменные окружения Vite

Адрес API можно хранить в `.env`:

```env
VITE_API_URL=https://example.com
```

Использование:

```js
const API_URL = import.meta.env.VITE_API_URL
```

В клиентский код попадают только переменные с префиксом `VITE_`. Они видны пользователю, поэтому в них нельзя хранить секретные ключи и пароли.

## Частые ошибки

- Нет проверки `response.ok` → ответ `404` или `500` не попадает в `catch`, `response.json()` падает на HTML-странице ошибки или в список записывается объект с описанием ошибки → проверять `response.ok` и бросать исключение с кодом статуса.
- Флаг загрузки выключается только в `try` → после ошибки «Загрузка...» висит навсегда → выключать `isLoading` в `finally`.
- Запрос отправляется на каждое нажатие клавиши в поле поиска → десятки запросов, ответы приходят вразнобой и старый результат перезаписывает новый → отменять предыдущий запрос через `onCleanup` и добавить debounce.
- Результат запроса присваивается после удаления компонента → лишняя работа, в консоли предупреждения об обновлении размонтированного компонента → отменять запрос через `AbortController` в `onUnmounted`.
- Секрет (ключ API, пароль к базе) записан в `VITE_*` → он попадает в сборку и виден любому пользователю в исходниках → хранить секреты только на backend, а во `VITE_*` — лишь публичные адреса.
- Одна и та же функция запроса скопирована в несколько компонентов → при смене адреса или формата ответа правки расползаются → вынести запросы в `src/api` и вызывать одну функцию.

## Когда не использовать

Если данные нужны нескольким страницам, не оставляйте запрос и состояние в компоненте: при каждом переходе список загружается заново, а компоненты держат разные копии. Перенесите загрузку в стор [Pinia](pinia.md) и вызывайте action из компонентов.

Ручной набор из `isLoading`, `error`, `AbortController` и повторов в каждом компоненте утомляет. В проекте с десятками запросов посмотрите на готовые библиотеки, например `useFetch` из VueUse или TanStack Query: они берут на себя кэширование, отмену и повторные попытки.

## Связанные темы

- [HTTP-запросы в JavaScript](../../languages/javascript/requests.md) — `fetch`, Axios, статусы и CORS
- [Pinia](pinia.md) — запросы в actions общего стора
- [Debounce и throttle во Vue](debounce_throttle.md) — задержка запроса при вводе в поле поиска
- [Жизненный цикл Vue](lifecycle.md) — `onMounted` и `onUnmounted`
