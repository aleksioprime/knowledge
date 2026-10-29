# Установка модулей

Голый Vue-проект умеет только отрисовывать компоненты. Как только появляются несколько страниц, общие данные для разных компонентов и готовые элементы интерфейса, к проекту подключают Vue Router, Pinia и Vuetify. Здесь — команды установки и минимальное подключение каждого модуля в `main.js`; подробный разбор работы с ними — в отдельных заметках.

## Минимальный пример

```bash
npm install vue-router pinia
```

```js
// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())   // хранилища доступны через useXStore() в любом компоненте
app.use(router)          // <router-view> и <router-link> доступны в шаблонах
app.mount('#app')
```

Плагины подключают до `app.mount`: после монтирования добавить их уже нельзя.

## Как это работает

### Установка Vue Router

**Vue Router** — это официальный маршрутизатор (router) для Vue.js, который позволяет создавать одностраничные приложения (SPA) с разными “страницами” и навигацией по ним без перезагрузки браузера.

Подробно маршруты, `RouterView`, `RouterLink`, параметры и navigation guards разобраны в разделе [Vue Router](router.md).

Установите Vue Router:

```
npm install vue-router
```

Импортируйте Vue-Router в main.js и подключите к проекту:

```js
// Импорт модуля навигации Vue Router
import router from "@/router";
...
// Подключем Vue Router для навигации
app.use(router);
...
```

Создайте файл `src/router/index.js`:

```js
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from "@/router/routes";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
```

Создайте файл `src/router/routes.js`:

```js
export const routes = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/HomeView.vue"),
  },
  {
    path: '/users', 
    name: "users",
    component: () => import("@/views/UserView.vue"),
    meta: {
      middlewares: [isLoggedIn],
    },
  },
]
```

Функция `isLoggedIn` в `meta.middlewares` — проверка доступа к маршруту; как её написать и подключить, разобрано в заметке [Добавление Middleware](middleware.md).

Попробуйте использовать в компоненте `App.vue`:

```vue
<template>
  <div>
    <nav>
      <router-link to="/">Главная</router-link>
      <router-link to="/users">Пользователи</router-link>
    </nav>
    <router-view />
  </div>
</template>
```

### Установка Pinia

**Pinia** — это современный менеджер состояния (state management library) для **Vue.js** (аналог Vuex, но проще и современнее). С помощью Pinia можно удобно хранить и изменять общие данные, к которым обращаются разные компоненты приложения.

Подробное описание state, getters, actions и Setup Store находится в разделе [Pinia: управление общим состоянием во Vue](pinia.md).

Установите `pinia`:

```sh
npm install pinia
```

Подключите в проект в `main.js`:

```js
import { createApp } from 'vue'
import App from './App.vue'
// Импорт функции
import { createPinia } from 'pinia'

const app = createApp(App)
// Подключение плагина
app.use(createPinia())
app.mount('#app')
```

Создайте папку `src/stores` и в файле `counter.js` попробуйте:

```js
import { defineStore } from 'pinia'

export const useCounterStore = defineStore('counter', {
  state: () => ({
    count: 0,
  }),
  actions: {
    increment() {
      this.count++
    },
    decrement() {
      this.count--
    },
  },
})
```

Попробуйте использовать в компоненте:

```js
<script setup>
import { useCounterStore } from '@/stores/counter'

// Получаем доступ к стору (store)
const counter = useCounterStore()
</script>

<template>
  <div>
    <h2>Counter: {{ counter.count }}</h2>
    <button @click="counter.increment">+</button>
    <button @click="counter.decrement">-</button>
  </div>
</template>
```

### Установка Vuetify

**Vuetify** — это популярная библиотека компонентов для фреймворка **Vue.js**, которая реализует стиль и принципы Material Design от Google.

Установите фреймворк vuetify:

```sh
npm install vuetify
```

Установите плагин:

```sh
npm install vite-plugin-vuetify
```

Установите пакет для иконок MDI:

```sh
npm install @mdi/font
```

Добавьте импорты в `main.js`:

```js
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
```

Добавьте создание объекта в main.js:

```js
const vuetify = createVuetify({
  components,
  directives,
})

...
app.use(vuetify);
...
```

Полный вариант настройки Vuetify с добавлением иконок MDI:

```js
// Импортируем функцию для создания приложения Vue
import { createApp } from 'vue'
// Импортируем главный компонент App.vue
import App from "@/App.vue";

// Импортируем стили, компоненты и директивы Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as vuetifyComponents from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Импортируем иконки Material Design Icons
import '@mdi/font/css/materialdesignicons.css'
// Импортируем алиасы и набор иконок MDI для Vuetify
import { aliases, mdi } from 'vuetify/iconsets/mdi'

// Создаём экземпляр Vuetify с нужными настройками
const vuetify = createVuetify({
	components: vuetifyComponents,
	directives,
	// Настройка иконок для приложения
	icons: {
		defaultSet: 'mdi',
		aliases,
		sets: {
			mdi,
		},
	},
})

// Создаём Vue-приложение, передавая главный компонент App
const app = createApp(App);
// Подключаем Vuetify как плагин
app.use(vuetify);
// Монтируем приложение в элемент с id="app"
app.mount("#app");
```

Добавьте плагин в `vite.config.js`:

```js
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
	plugins: [
		vue(),
		vuetify({ autoImport: true }),
	],
	resolve: {
		alias: {
			'@': fileURLToPath(new URL('./src', import.meta.url)),
		},
	},
})
```

Попробуйте использовать компонент:

```vue
<template>
  <v-app>
    <v-main>
      <v-container>
        <v-btn color="primary">Привет, Vuetify!</v-btn>
      </v-container>
    </v-main>
  </v-app>
</template>
```

## Частые ошибки

- `app.use(router)` вызван после `app.mount('#app')` → `<router-view>` остаётся пустым, в консоли `Failed to resolve component: router-view` → подключать все плагины до `mount`.
- `useCounterStore()` вызван на уровне модуля (например, в `routes.js` при импорте), а не внутри функции → `getActivePinia() was called but there was no active Pinia` → вызывать стор внутри `setup`, обработчика или navigation guard, когда Pinia уже подключена.
- В `routes.js` используется `isLoggedIn`, но импорта нет → `ReferenceError: isLoggedIn is not defined` при загрузке приложения → импортировать функцию из файла с middleware.
- Компоненты Vuetify используются без импорта `vuetify/styles` или вне `<v-app>` → кнопки и сетка отрисовываются без стилей, выпадающие списки «ломают» вёрстку → импортировать стили в `main.js` и обернуть корневой шаблон в `<v-app>`.
- Иконки `mdi-*` показываются пустыми квадратами → не установлен `@mdi/font` или не импортирован `materialdesignicons.css` → поставить пакет, импортировать стили и указать `icons.defaultSet: 'mdi'`.

## Когда не использовать

Vue Router лишний в приложении из одного экрана: виджет, форма или дашборд без переходов обходятся условным рендерингом (`v-if`) и не нуждаются в URL для каждого состояния. Pinia лишняя, пока данные нужны только паре соседних компонентов: передачу «родитель → ребёнок» делайте через `props` и события, а для глубокой вложенности подойдёт `provide` / `inject`.

Vuetify тянет большой набор компонентов и стилей и диктует Material Design. Для небольшого проекта с собственным дизайном проще написать несколько компонентов на обычном CSS или взять легковесную библиотеку без визуального каркаса.

## Связанные темы

- [Установка проекта](install_basic.md) — базовый проект, в который ставятся модули
- [Vue Router](router.md) — маршруты, параметры и navigation guards
- [Добавление Middleware](middleware.md) — проверки перед переходом по маршруту
- [Pinia: управление общим состоянием](pinia.md) — state, getters, actions
- [Дополнительные модули](extra_modules.md) — Axios, jwt-decode и VueUse
