Создайте файл `src/middlewares/middlewarePipeline`:

```js
// Экспортируем функцию middlewarePipeline, принимающую экземпляр роутера
export const middlewarePipeline = (router) => {
  // Регистрируем глобальный "beforeEach" guard на роутере
  router.beforeEach(async (to, from) => {
    // Получаем список middleware из meta маршрута
    const middlewares = to.meta.middlewares;
    // Если у маршрута нет middleware — разрешаем переход (return true)
    if (!middlewares) {
      return true;
    }
    // Если есть — проходим по всем middleware в порядке очереди
    for (const middleware of middlewares) {
      // Вызываем каждое middleware, передаём ему параметры (to, from, router) (можно добавить дополнительные параметры по необходимости)
      const result = await middleware({ to, from, router });
      // Проверяем, что вернуло middleware:
      // - если объект (например, { name: 'login' }) — делаем редирект на другой маршрут
      // - если строка (например, '/login') — тоже редиректим
      // - если false — отменяем переход
      if (
        typeof result === "object" ||
        typeof result === "string" ||
        result === false
      ) {
        return result; // Возвращаем результат
      }
    }
    // Если ни одно middleware не остановило переход — разрешаем переход дальше
    return true;
  });
};
```

Добавьте пайплайн в `src/router/index.js`:

```js
// Импортируем функции для создания роутера и истории навигации из vue-router
import { createRouter, createWebHistory } from 'vue-router'

// Импортируем массив маршрутов из отдельного файла
import { routes } from "@/router/routes"

// Импортируем функцию для подключения middleware цепочки
import { middlewarePipeline } from "@/middlewares/middlewarePipeline"

// Создаём экземпляр роутера, передаём ему историю и маршруты
const router = createRouter({
  // Используем HTML5 History API для управления навигацией (красивые адреса без #)
  history: createWebHistory(import.meta.env.BASE_URL),
  // Массив маршрутов приложения
  routes,
})

// Подключаем обработку middleware: теперь при переходе по маршрутам
// будут срабатывать все указанные в meta.middlewares функции
middlewarePipeline(router)

// Экспортируем роутер для использования в основном файле приложения (main.js)
export default router
```

Создайте middleware, например, проверка авторизации в `src/middlewares/isLoggedIn`: 

```js
export default function isLoggedIn({ to, from }) {
  // Например, проверить, залогинен ли пользователь
  const isAuth = Boolean(localStorage.getItem('token'));
  if (!isAuth) {
    // redirect (или false, чтобы отменить переход)
    return { name: 'login' }; // редирект на страницу логина
  }
  return true;
}
```

Можете добавлять этот middleware в пути маршрутов в раздел `meta`:

```js
import { isLoggedIn } from "@/middlewares/isLoggedIn";

const routes = [
  {
    path: '/dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: {
      middlewares: [isLoggedIn],
    },
  },
  ...
]
```