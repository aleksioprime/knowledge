# HTTP-запросы во Vue

Базовая работа с HTTP, `fetch`, Axios, JSON, статусами и CORS описана в разделе [HTTP-запросы в JavaScript](../javascript/requests.md).

Здесь рассматривается только интеграция запросов с Vue-приложением.

## Реактивное состояние запроса

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

## API-модули

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

## Запросы в Pinia

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

## Отмена при удалении компонента

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

## Запрос при изменении значения

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

## Переменные окружения Vite

Адрес API можно хранить в `.env`:

```env
VITE_API_URL=https://example.com
```

Использование:

```js
const API_URL = import.meta.env.VITE_API_URL
```

В клиентский код попадают только переменные с префиксом `VITE_`. Они видны пользователю, поэтому в них нельзя хранить секретные ключи и пароли.
