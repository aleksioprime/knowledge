# Middleware в Vue Router

Проверка авторизации, роли, заполненного профиля — такие условия нужны сразу на многих страницах. Писать их в одном большом `router.beforeEach` с цепочкой `if` неудобно: условия перемешиваются, а понять, что требует конкретный маршрут, по его описанию нельзя. Промежуточный обработчик (middleware) — отдельная функция с одной проверкой, которую маршрут подключает через `meta`, а общий конвейер (pipeline) вызывает их по очереди.

## Минимальный пример

```js
import { createRouter, createWebHistory } from 'vue-router'

const isLoggedIn = ({ to }) => {
  if (!localStorage.getItem('token')) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
    { path: '/tasks', component: () => import('@/views/Tasks.vue'), meta: { middlewares: [isLoggedIn] } },
  ],
})

router.beforeEach(async (to, from) => {
  for (const middleware of to.meta.middlewares ?? []) {
    const result = await middleware({ to, from, router })
    if (result === false || typeof result === 'object' || typeof result === 'string') {
      return result  // редирект или отмена перехода
    }
  }
  return true
})

// без token в localStorage переход на /tasks превращается в /login?redirect=/tasks
```

## Как это работает

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

## Частые ошибки

- Middleware ничего не возвращает в разрешающей ветке → в конвейере `undefined` не считается остановкой, но при ошибке в логике переход тихо проходит без проверки → всегда возвращать `true` явно, а в конвейере прерывать цикл только на объекте, строке или `false`.
- Middleware редиректит на страницу входа, которая сама защищена тем же middleware → бесконечный цикл редиректов и ошибка `Infinite redirect in navigation guard` → не подключать проверку авторизации к маршруту `login` или проверять `to.name` внутри middleware.
- Файл экспортирует `export default`, а маршруты импортируют `{ isLoggedIn }` → импорт равен `undefined`, конвейер падает с `middleware is not a function` → согласовать способ экспорта и импорта.
- Middleware читает `localStorage` напрямую, а состояние входа живёт в Pinia → после `logout` без перезагрузки страницы токен в хранилище уже удалён, а стор ещё нет, или наоборот → проверять один источник правды, например стор авторизации, и чистить его вместе с хранилищем.
- Асинхронный middleware вызывается без `await` → конвейер получает промис, `typeof result === 'object'` возвращает его как «редирект» → всегда ждать результат через `await`.

## Когда не использовать

Если проверка одна и нужна на двух-трёх маршрутах, конвейер лишний: достаточно поля `meta.requiresAuth` и одного `router.beforeEach`, как показано в [защите маршрутов](auth.md#защита-маршрутов). Конвейер окупается, когда проверок несколько и они комбинируются по-разному на разных страницах.

Middleware на фронтенде не защищает данные: пользователь может вызвать API напрямую. Права на данные проверяет backend, а middleware только скрывает страницы и делает интерфейс понятнее.

## Связанные темы

- [Vue Router](router.md) — `meta`-поля и navigation guards, на которых построен конвейер
- [Аутентификация и авторизация во Vue](auth.md) — что проверять в middleware и где хранить токен
- [Pinia](pinia.md) — стор, из которого middleware читает состояние входа
