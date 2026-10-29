# Pinia: управление общим состоянием во Vue

Список задач нужен и на главной странице, и в шапке со счётчиком, и в форме редактирования. Передавать его через `props` сквозь пять уровней компонентов и собирать события обратно — путь, который быстро превращается в клубок. Хранилище (store) Pinia держит такие данные в одном месте: любой компонент получает тот же стор, читает его состояние и вызывает его методы.

## Минимальный пример

Стор обычно лежит в отдельном файле, здесь он объявлен рядом с компонентом ради краткости. Приложение должно подключить Pinia: `app.use(createPinia())`.

```vue
<script setup>
import { computed, ref } from 'vue'
import { defineStore, storeToRefs } from 'pinia'

const useTaskStore = defineStore('tasks', () => {
  const tasks = ref([{ title: 'Купить хлеб', done: false }])
  const doneCount = computed(() => tasks.value.filter((task) => task.done).length)
  function add(title) {
    tasks.value.push({ title, done: false })
  }
  return { tasks, doneCount, add }
})

const taskStore = useTaskStore()
const { tasks, doneCount } = storeToRefs(taskStore)
</script>

<template>
  <p>Выполнено: {{ doneCount }} из {{ tasks.length }}</p>  <!-- Выполнено: 0 из 1 -->
  <button @click="taskStore.add('Позвонить в банк')">Добавить</button>  <!-- после клика: 0 из 2 -->
</template>
```

## Как это работает

### Что такое Pinia

Pinia — официальная библиотека управления состоянием для Vue. Она хранит данные и бизнес-логику, которые не принадлежат одному конкретному компоненту.

Хранилище Pinia обычно называют **store** или **стор**. Компоненты могут получать один и тот же стор, читать его состояние и вызывать его методы.

Примеры данных, которые удобно хранить в Pinia:

- текущий пользователь и состояние авторизации;
- товары в корзине;
- список постов, используемый на нескольких страницах;
- глобальные фильтры;
- уведомления приложения.

Локальное состояние одного компонента, например открыто ли его меню, обычно лучше оставить в `ref()` внутри этого компонента.

### Установка

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

### Основные части стора

В сторе обычно есть три вида сущностей:

- **state** — хранимые данные, аналог `ref()` или `data`;
- **getters** — вычисляемые значения, аналог `computed()`;
- **actions** — функции, которые читают и изменяют состояние.

### Setup Store

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

### Использование стора в компоненте

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

### Деструктуризация и `storeToRefs`

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

### Асинхронные actions

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

### Option Store

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

## Частые ошибки

- Деструктуризация `const { count } = useCounterStore()` → значение скопировано один раз и не обновляется вместе со стором → брать state и getters через `storeToRefs()`, а actions можно деструктурировать напрямую.
- Стор вызывается вне компонента до `app.use(pinia)`, например на верхнем уровне `router/index.js` → ошибка `getActivePinia() was called but there was no active Pinia` → вызывать `useXxxStore()` внутри `setup`, guard или action, а не при импорте модуля.
- Setup Store не возвращает часть `ref` → данные не видны в компонентах и в инструментах разработчика, не сохраняются в SSR → возвращать из функции все state, getters и actions.
- Два стора объявлены с одним идентификатором `defineStore('counter', ...)` → сторы перезаписывают друг друга, в инструментах разработчика один из них пропадает → давать каждому стору уникальное имя.
- Локальное состояние компонента (открыт ли модальный диалог, текст в поле ввода) вынесено в стор → состояние «утекает» между страницами, после ухода диалог остаётся открытым → хранить в Pinia только то, что нужно нескольким компонентам.

## Когда не использовать

Если данные нужны одному компоненту или паре «родитель — ребёнок», стор лишний: достаточно `ref()` в компоненте, `props` и событий. Для передачи значения вглубь дерева без промежуточных `props` подойдут `provide`/`inject` из заметки [Пользовательские возможности Vue](vue_custom.md#provide-и-inject).

Переиспользуемую логику без общего состояния (таймер, координаты мыши, пагинация для конкретного списка) лучше оформить как composable-функцию: каждый вызов создаёт своё независимое состояние, тогда как стор Pinia всегда один на приложение.

## Связанные темы

- [Реактивность в Vue](reactivity.md) — `ref()` и `computed()`, из которых собран Setup Store
- [HTTP-запросы во Vue](http_requests.md) — запросы в actions
- [Аутентификация и авторизация во Vue](auth.md) — стор авторизации как типичный пример
- [Mixins и composables](mixins_composables.md) — переиспользование логики без общего состояния
