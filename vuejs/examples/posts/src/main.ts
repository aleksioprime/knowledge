import { createApp } from 'vue'
import App from './App.vue'
import { createPinia } from 'pinia'
import './assets/main.css'
import { router } from './routes'

const pinia = createPinia()

// Создаём Vue-приложение
const app = createApp(App)
// Подключаем плагин Pinia к приложению Vue
app.use(pinia)
// Подключаем роутер к приложению Vue
app.use(router)
// Подключаем его к элементу #app из index.html
app.mount('#app')
