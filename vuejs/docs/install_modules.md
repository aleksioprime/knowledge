### Установка Vue Router

**Vue Router** — это официальный маршрутизатор (router) для Vue.js, который позволяет создавать одностраничные приложения (SPA) с разными “страницами” и навигацией по ним без перезагрузки браузера.

Подробно маршруты, `RouterView`, `RouterLink`, параметры и navigation guards разобраны в разделе [Vue Router](vue_router.md).

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

Попробуй использовать в компоненте `App.vue`:

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

**Pinia** — это современный менеджер состояния (state management library) для **Vue.js** (аналог Vuex, но проще и современнее). С помощью Pinia ты можешь удобно хранить и изменять общие данные, к которым обращаются разные компоненты твоего приложения.

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

Установи фреймворк vuetify:

```sh
npm install vuetify
```

Установи плагин:

```sh
npm install vite-plugin-vuetify
```

Установи пакет для иконок MDI:

```sh
npm install @mdi/font
```

Добавь импорты в `main.js`:

```js
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
```

Добавь создание объекта в main.js:

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

Попробуй использовать компонент:

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
