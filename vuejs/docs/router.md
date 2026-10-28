# Vue Router

## Что такое Vue Router

Vue Router — официальный маршрутизатор для Vue. Он связывает URL браузера с компонентами приложения.

Например:

```text
/             → главная страница
/posts        → список постов
/posts/42     → пост с id 42
/profile      → профиль пользователя
```

В SPA переход между маршрутами обычно не перезагружает весь HTML-документ. Vue Router меняет URL и отображает нужный компонент внутри `RouterView`.

## Установка

```sh
npm install vue-router
```

## Базовая структура

```text
src/
├── views/
│   ├── HomeView.vue
│   ├── PostsView.vue
│   └── NotFoundView.vue
├── router.js
├── App.vue
└── main.js
```

Компоненты из `views` являются обычными Vue-компонентами. Название `View` лишь показывает, что компонент используется как страница маршрута.

## Создание router

Создайте `src/router.js`:

```js
import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '@/views/HomeView.vue'
import PostsView from '@/views/PostsView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/posts',
    name: 'posts',
    component: PostsView,
  },
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})
```

Основные свойства маршрута:

- `path` — адрес страницы;
- `name` — уникальное имя маршрута;
- `component` — компонент, который будет отображён;
- `children` — вложенные маршруты;
- `meta` — дополнительные данные маршрута.

## Подключение к приложению

```js
// main.js
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'

const app = createApp(App)

app.use(router)
app.mount('#app')
```

`app.use(router)` подключает плагин и делает доступными:

- `RouterView`;
- `RouterLink`;
- `useRouter()`;
- `useRoute()`;
- `$router` и `$route` в шаблонах.

## RouterView

`RouterView` определяет место, в котором будет отображаться компонент текущего маршрута:

```vue
<template>
  <header>Шапка сайта</header>

  <main>
    <RouterView />
  </main>

  <footer>Подвал сайта</footer>
</template>
```

При переходе между страницами шапка и подвал остаются, а содержимое `RouterView` меняется.

Если в приложении нет `RouterView`, компоненты маршрутов не будут видны.

## RouterLink

Для внутренней навигации используется `RouterLink`:

```vue
<template>
  <nav>
    <RouterLink to="/">Главная</RouterLink>
    <RouterLink to="/posts">Посты</RouterLink>
  </nav>
</template>
```

В отличие от обычного `<a>`, `RouterLink` переключает маршрут без полной перезагрузки страницы.

Предпочтительно ссылаться на именованный маршрут:

```vue
<RouterLink :to="{ name: 'posts' }">Посты</RouterLink>
```

Если адрес `/posts` позже изменится, ссылка по имени продолжит работать.

### Активная ссылка

Vue Router автоматически добавляет активным ссылкам классы:

- `router-link-active`;
- `router-link-exact-active`.

```css
.router-link-active {
  font-weight: bold;
}
```

`router-link-active` применяется и к ссылкам на родительские маршруты. `router-link-exact-active` добавляется только при точном совпадении и не включает родительские маршруты.

Например, если маршрут `/users/:id` содержит дочерний маршрут `settings` и открыт адрес `/users/7/settings`, ссылки на `/users/7` и `/users/7/settings` получат `router-link-active`. Класс `router-link-exact-active` получит только ссылка на `/users/7/settings`.

Названия классов можно изменить для отдельной ссылки через props `active-class` и `exact-active-class`:

```vue
<RouterLink
  :to="{ name: 'posts' }"
  active-class="nav-link--active"
  exact-active-class="nav-link--exact"
>
  Посты
</RouterLink>
```

```css
.nav-link--active {
  color: royalblue;
}

.nav-link--exact {
  font-weight: bold;
}
```

- `active-class` заменяет стандартный класс `router-link-active` для этой ссылки;
- `exact-active-class` заменяет стандартный класс `router-link-exact-active` для этой ссылки.

При точном совпадении ссылка обычно получает оба указанных класса. Эти props изменяют только имена CSS-классов, но не правила сопоставления маршрутов.

Чтобы переименовать классы сразу для всех `RouterLink`, задайте `linkActiveClass` и `linkExactActiveClass` при создании роутера:

```js
const router = createRouter({
  history: createWebHistory(),
  routes,
  linkActiveClass: 'nav-link--active',
  linkExactActiveClass: 'nav-link--exact',
})
```

При определении активной ссылки Vue Router сравнивает записи маршрутов и значения `params`. Параметры строки запроса (`query`) при этом не учитываются.

## Динамические параметры

Динамическая часть пути начинается с `:`:

```js
{
  path: '/posts/:postId',
  name: 'post',
  component: () => import('@/views/PostView.vue'),
}
```

Адрес `/posts/42` создаст параметр:

```js
route.params.postId // '42'
```

Ссылка с параметром:

```vue
<RouterLink
  :to="{
    name: 'post',
    params: { postId: post.id },
  }"
>
  {{ post.title }}
</RouterLink>
```

## useRoute

`useRoute()` возвращает реактивный объект текущего маршрута:

```vue
<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

console.log(route.name)
console.log(route.path)
console.log(route.params.postId)
console.log(route.query.page)
</script>
```

Частые свойства `route`:

- `route.name` — имя;
- `route.path` — путь;
- `route.fullPath` — путь вместе с query и hash;
- `route.params` — динамические параметры;
- `route.query` — query-параметры;
- `route.meta` — дополнительные данные.

Объект `route` реактивен. Обычно наблюдают за конкретным параметром, а не за всем объектом:

```js
import { watch } from 'vue'

watch(
  () => route.params.postId,
  (postId) => loadPost(postId),
)
```

## Query-параметры

Query-параметры находятся после `?`:

```text
/posts?page=2&sort=new
```

Ссылка:

```vue
<RouterLink
  :to="{
    name: 'posts',
    query: { page: 2, sort: 'new' },
  }"
>
  Вторая страница
</RouterLink>
```

Чтение:

```js
const route = useRoute()

console.log(route.query.page) // '2'
console.log(route.query.sort) // 'new'
```

Значения query-параметров, прочитанные из URL, обычно являются строками. Если нужно число, его следует преобразовать:

```js
const page = Number(route.query.page ?? 1)
```

## Программная навигация

`useRouter()` возвращает экземпляр маршрутизатора:

```vue
<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function openPost(postId) {
  router.push({
    name: 'post',
    params: { postId },
  })
}
</script>
```

Основные методы:

```js
// Добавить адрес в историю.
router.push({ name: 'posts' })

// Заменить текущий адрес без новой записи в истории.
router.replace({ name: 'login' })

// Вернуться назад.
router.back()

// Перейти вперёд.
router.forward()

// Переместиться по истории браузера.
router.go(-2)
```

`push()` позволяет вернуться назад кнопкой браузера. `replace()` заменяет текущую запись истории.

## Вложенные маршруты

Вложенный `RouterView` позволяет создать общий layout для группы страниц.

```js
const routes = [
  {
    path: '/profile',
    component: () => import('@/views/ProfileLayout.vue'),
    children: [
      {
        path: '',
        name: 'profile',
        component: () => import('@/views/ProfileOverviewView.vue'),
      },
      {
        path: 'settings',
        name: 'profile-settings',
        component: () => import('@/views/ProfileSettingsView.vue'),
      },
    ],
  },
]
```

Обратите внимание: путь дочернего маршрута записывается без начального `/`.

`ProfileLayout.vue` должен содержать свой `RouterView`:

```vue
<template>
  <h1>Профиль</h1>

  <nav>
    <RouterLink :to="{ name: 'profile' }">Обзор</RouterLink>
    <RouterLink :to="{ name: 'profile-settings' }">Настройки</RouterLink>
  </nav>

  <RouterView />
</template>
```

## Redirect и страница 404

Перенаправление:

```js
{
  path: '/home',
  redirect: { name: 'home' },
}
```

Маршрут для неизвестных адресов размещают последним:

```js
{
  path: '/:pathMatch(.*)*',
  name: 'not-found',
  component: () => import('@/views/NotFoundView.vue'),
}
```

## Lazy loading

Компоненты маршрутов можно загружать только при первом открытии страницы:

```js
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/posts',
    name: 'posts',
    component: () => import('@/views/PostsView.vue'),
  },
]
```

Vite создаст отдельные JavaScript-файлы для таких маршрутов. Это уменьшает начальный размер приложения.

Для route-компонентов достаточно функции с динамическим `import()`. Оборачивать её в `defineAsyncComponent()` не нужно.

## Meta-поля

`meta` хранит дополнительные данные маршрута:

```js
{
  path: '/profile',
  name: 'profile',
  component: () => import('@/views/ProfileView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Профиль',
  },
}
```

Получение данных:

```js
const route = useRoute()

console.log(route.meta.requiresAuth)
console.log(route.meta.title)
```

## Navigation guards

Guard выполняется перед переходом и может разрешить, отменить или перенаправить навигацию.

Глобальная проверка авторизации:

```js
router.beforeEach((to) => {
  const isAuthenticated = Boolean(localStorage.getItem('accessToken'))

  if (to.meta.requiresAuth && !isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }
})
```

Guard может вернуть:

- ничего — разрешить переход;
- `false` — отменить переход;
- строку или объект маршрута — перенаправить;
- `Promise` — дождаться асинхронной проверки.

Не перенаправляйте пользователя на тот же защищённый маршрут: это создаст бесконечный цикл.

### Guards в компонентах

```vue
<script setup>
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'

onBeforeRouteUpdate((to, from) => {
  if (to.params.postId !== from.params.postId) {
    loadPost(to.params.postId)
  }
})

onBeforeRouteLeave(() => {
  if (hasUnsavedChanges.value) {
    return window.confirm('Уйти без сохранения?')
  }
})
</script>
```

`onBeforeRouteUpdate()` полезен, когда меняется параметр, но используется тот же экземпляр компонента. `onBeforeRouteLeave()` позволяет предупредить о несохранённых изменениях.

## Передача params как props

Компонент страницы можно отвязать от `useRoute()` и передать параметры через props («возьми параметры из URL и передай их компоненту как обычные props».):

```js
{
  path: '/posts/:postId',
  name: 'post',
  component: () => import('@/views/PostView.vue'),
  props: true,
}
```

```vue
<script setup>
defineProps({
  postId: {
    type: String,
    required: true,
  },
})
</script>
```

Так компонент проще переиспользовать и тестировать

Официальная документация: [router.vuejs.org](https://router.vuejs.org/guide/).
