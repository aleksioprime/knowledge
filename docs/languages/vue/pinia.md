# Pinia: управление общим состоянием во Vue

## Что такое Pinia

Pinia — официальная библиотека управления состоянием для Vue. Она хранит данные и бизнес-логику, которые не принадлежат одному конкретному компоненту.

Хранилище Pinia обычно называют **store** или **стор**. Компоненты могут получать один и тот же стор, читать его состояние и вызывать его методы.

Примеры данных, которые удобно хранить в Pinia:

- текущий пользователь и состояние авторизации;
- товары в корзине;
- список постов, используемый на нескольких страницах;
- глобальные фильтры;
- уведомления приложения.

Локальное состояние одного компонента, например открыто ли его меню, обычно лучше оставить в `ref()` внутри этого компонента.

## Установка

```sh
npm install pinia
```

Создайте экземпляр Pinia и подключите его к Vue-приложению в `main.js`:

```js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')
```

`app.use(pinia)` делает сторы доступными компонентам приложения.

## Основные части стора

В сторе обычно есть три вида сущностей:

- **state** — хранимые данные, аналог `ref()` или `data`;
- **getters** — вычисляемые значения, аналог `computed()`;
- **actions** — функции, которые читают и изменяют состояние.

## Setup Store

Setup Store похож на обычный `<script setup>` компонента. В нём используются знакомые функции `ref()` и `computed()`.

Создайте файл `src/stores/counterStore.js`:

```js
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useCounterStore = defineStore('counter', () => {
  // State: данные стора.
  const count = ref(0)

  // Getter: значение, вычисляемое из state.
  const doubleCount = computed(() => count.value * 2)

  // Action: действие, которое изменяет state.
  function increment() {
    count.value++
  }

  // Компонентам доступны только возвращённые значения и функции.
  return {
    count,
    doubleCount,
    increment,
  }
})
```

Первый аргумент `defineStore()` — уникальный идентификатор стора:

```js
defineStore('counter', ...)
```

Имя экспортируемой функции принято начинать с `use` и заканчивать на `Store`:

```js
useCounterStore
useAuthStore
usePostStore
```

В Setup Store:

- `ref()` становится state;
- `computed()` становится getter;
- обычная функция становится action.

Все свойства состояния Setup Store нужно вернуть из функции. Это необходимо для корректной работы инструментов разработчика, SSR и плагинов Pinia.

## Использование стора в компоненте

```vue
<script setup>
import { useCounterStore } from '@/stores/counterStore'

const counterStore = useCounterStore()
</script>

<template>
  <p>Счётчик: {{ counterStore.count }}</p>
  <p>Удвоенное значение: {{ counterStore.doubleCount }}</p>
  <button @click="counterStore.increment">Увеличить</button>
</template>
```

В шаблоне `.value` не нужен. Pinia и Vue автоматически разворачивают реактивные значения:

```vue
{{ counterStore.count }}
```

## Деструктуризация и `storeToRefs`

Обычная деструктуризация состояния стора нарушает реактивность:

```js
const counterStore = useCounterStore()

// Неправильно: count перестанет обновляться вместе со стором.
const { count } = counterStore
```

Для state и getters используйте `storeToRefs()`:

```js
import { storeToRefs } from 'pinia'

const counterStore = useCounterStore()
const { count, doubleCount } = storeToRefs(counterStore)
```

Внутри `<script setup>` полученные значения являются `ref`:

```js
console.log(count.value)
```

Actions можно деструктурировать напрямую, потому что они не являются реактивными данными:

```js
const { increment } = counterStore
```

Если деструктуризация не нужна, проще обращаться к значениям через сам стор:

```js
counterStore.count
counterStore.increment()
```

## Асинхронные actions

Actions могут выполнять HTTP-запросы. Компоненту тогда не нужно знать, откуда приходят данные и как они сохраняются.

```js
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getPosts } from '@/api/posts'

export const usePostStore = defineStore('posts', () => {
  const posts = ref([])
  const isLoading = ref(false)
  const error = ref('')

  async function loadPosts() {
    isLoading.value = true
    error.value = ''

    try {
      const response = await getPosts(10, posts.value.length)
      posts.value.push(...response.items)
    } catch (requestError) {
      error.value =
        requestError instanceof Error ? requestError.message : 'Не удалось загрузить посты'
    } finally {
      isLoading.value = false
    }
  }

  return {
    posts,
    isLoading,
    error,
    loadPosts,
  }
})
```

Компонент вызывает action и отображает состояние:

```vue
<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { usePostStore } from '@/stores/postStore'

const postStore = usePostStore()
const { posts, isLoading, error } = storeToRefs(postStore)

onMounted(postStore.loadPosts)
</script>

<template>
  <p v-if="isLoading">Загрузка...</p>
  <p v-else-if="error">{{ error }}</p>
  <PostsList v-else :posts="posts" />
</template>
```

## Option Store

Pinia также поддерживает синтаксис, похожий на Options API:

```js
import { defineStore } from 'pinia'

export const useCounterStore = defineStore('counter', {
  state: () => ({
    count: 0,
  }),

  getters: {
    doubleCount: (state) => state.count * 2,
  },

  actions: {
    increment() {
      this.count++
    },
  },
})
```

- `state` похож на `data()`;
- `getters` похожи на `computed`;
- `actions` похожи на `methods`.

Setup Store и Option Store равноправны. Для проекта с Composition API и `<script setup>` обычно удобно использовать Setup Store, потому что его синтаксис совпадает с синтаксисом компонентов.

Официальная документация: [pinia.vuejs.org](https://pinia.vuejs.org/)
