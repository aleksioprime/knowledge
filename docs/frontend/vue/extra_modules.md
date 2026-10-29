# Дополнительные модули

Кроме роутера и хранилища, почти в каждом Vue-проекте нужны ещё три вещи: удобные HTTP-запросы к backend, чтение срока действия и полей JWT-токена на клиенте и готовые composables для типовых задач вроде debounce или работы с `localStorage`. Писать это самому дольше, чем подключить Axios, jwt-decode и VueUse; здесь — что это за пакеты, как их поставить и когда они не нужны.

## Минимальный пример

```bash
npm install axios jwt-decode @vueuse/core
```

```js
import axios from 'axios'
import { jwtDecode } from 'jwt-decode'
import { useLocalStorage } from '@vueuse/core'

const api = axios.create({ baseURL: '/api' })
const token = useLocalStorage('access_token', '')   // ref, синхронизированный с localStorage

const { data } = await api.post('/auth/login', { email: 'user@example.com', password: 'secret' })
token.value = data.access
console.log(jwtDecode(token.value).exp)   // 1761734400 — срок действия токена (unix time)
```

## Как это работает

### Axios

Axios — библиотека для HTTP-запросов поверх `XMLHttpRequest`. В отличие от `fetch`, она сама разбирает JSON, считает ответы с кодом 4xx и 5xx ошибками и позволяет задать общий `baseURL`, заголовки и перехватчики (interceptors) для всех запросов приложения.

Установите Axios:

```
npm install axios
```

Базовые примеры Fetch и Axios находятся в разделе [HTTP-запросы в JavaScript](../../languages/javascript/requests.md), а интеграция с Vue — в разделе [HTTP-запросы во Vue](http_requests.md).

### jwt-decode

jwt-decode разбирает полезную нагрузку (payload) JWT-токена без проверки подписи: из строки токена получается обычный объект с полями вроде `exp`, `sub` и `role`. Этого достаточно, чтобы на клиенте понять, не истёк ли токен, и показать имя пользователя; проверять права по этим полям должен backend.

Установите jwt-decode:

```
npm install jwt-decode
```

Начиная с версии 4 пакет экспортирует именованную функцию: `import { jwtDecode } from 'jwt-decode'`. Как хранить токен и обновлять его по refresh-токену, разобрано в заметке [Аутентификация и авторизация во Vue](auth.md).

### VueUse

VueUse — коллекция composables для Composition API: `useLocalStorage`, `useDebounceFn`, `useFetch`, `useEventListener`, `useIntersectionObserver` и сотни других. Каждая функция возвращает реактивные значения и сама снимает подписки при размонтировании компонента.

Установите VueUse:

```
npm install @vueuse/core
```

Функции из VueUse вызывают внутри `<script setup>` или другого composable, как и собственные хуки на Composition API.

## Частые ошибки

- `import jwt_decode from 'jwt-decode'` по старым примерам → с версии 4 `TypeError: jwt_decode is not a function` → использовать именованный импорт `import { jwtDecode } from 'jwt-decode'`.
- Права пользователя проверяются по полю `role` из `jwtDecode` → токен можно подделать в браузере, и клиент покажет чужие разделы → на клиенте использовать поля только для отображения и срока действия, доступ к данным проверять на backend.
- Абсолютный адрес backend в каждом вызове `axios.get('http://localhost:8000/api/...')` → при переезде на другой адрес или в Docker правки по всему проекту → создать один экземпляр `axios.create({ baseURL })` и импортировать его.
- Composable из VueUse вызван в обработчике клика или в обычной функции → предупреждение `onUnmounted is called when there is no active component instance`, подписки не снимаются → вызывать `useXxx()` на верхнем уровне `<script setup>`.
- `@vueuse/core` установлен ради одной функции → лишняя зависимость и обновления → написать функцию самому, например debounce из заметки [Debounce, throttle и связанные техники](debounce_throttle.md).

## Когда не использовать

Для двух-трёх запросов без общих заголовков и перехватчиков хватает встроенного `fetch`: Axios добавляет зависимость ради удобств, которые в маленьком проекте не используются. jwt-decode не нужен, если backend хранит сессию в httpOnly-cookie: токен недоступен из JavaScript, а состояние входа узнаётся запросом вроде `/me`.

VueUse окупается, когда из неё берут десяток функций. Если нужна одна-две, проще написать их самому: так в проекте нет «чёрного ящика», а поведение полностью под контролем.

## Связанные темы

- [HTTP-запросы во Vue](http_requests.md) — Axios в компонентах и сервисах
- [Аутентификация и авторизация во Vue](auth.md) — где хранить и как обновлять JWT
- [Debounce, throttle и связанные техники](debounce_throttle.md) — что VueUse делает за вас
- [Установка модулей](install_modules.md) — Vue Router, Pinia и Vuetify
- [HTTP-запросы в JavaScript](../../languages/javascript/requests.md) — `fetch` и Axios без Vue
