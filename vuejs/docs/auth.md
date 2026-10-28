# Аутентификация и авторизация во Vue

Аутентификация отвечает на вопрос «кто пользователь?», а авторизация — «что ему разрешено?». Vue управляет формой входа и состоянием интерфейса, но проверять пароль, сессию, токен, роль и доступ к данным обязан backend.

## Основные подходы

### Серверная сессия и cookie

После входа backend создаёт сессию и отправляет браузеру cookie с непрозрачным идентификатором. Состояние сессии хранится на сервере, а браузер автоматически прикладывает cookie к запросам.

Для production обычно используют cookie с атрибутами `HttpOnly`, `Secure` и подходящим `SameSite`. `HttpOnly` не позволяет JavaScript прочитать идентификатор сессии. При cookie-аутентификации backend также должен защищаться от CSRF.

Этот подход удобен для собственного frontend и backend, особенно если они работают на одном домене или используется BFF (Backend for Frontend).

### JWT

JWT (JSON Web Token) — формат токена, а не отдельный способ ввода логина и пароля. Он состоит из трёх частей:

```text
header.payload.signature
```

Payload обычно содержит claims, например `sub`, `roles`, `exp`, `iss` и `aud`. JWT обычно подписан, но не зашифрован: его содержимое можно прочитать, поэтому в payload нельзя помещать пароли и другие секреты.

После входа API может вернуть короткоживущий access token. Клиент передаёт его в защищённых запросах:

```ts
await apiClient.get('/api/v1/users/me', {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
})
```

Backend для каждого запроса должен проверить подпись, срок действия и ожидаемые `issuer` и `audience`. Декодирование JWT на frontend удобно для отображения данных, но не доказывает подлинность токена и не заменяет серверную проверку.

Для продления сессии может применяться refresh token:

- access token живёт недолго и используется для API-запросов;
- refresh token живёт дольше и выдаёт новую пару токенов;
- refresh token нужно ротировать и отзывать при выходе или подозрительной активности.

### OAuth 2.0 и OpenID Connect

OAuth 2.0 предназначен для делегирования доступа к ресурсам, а OpenID Connect (OIDC) добавляет аутентификацию пользователя. Этот вариант применяется для входа через Google, Microsoft, корпоративный Identity Provider и другие внешние системы.

Для браузерного приложения используется Authorization Code Flow с PKCE:

1. приложение перенаправляет пользователя к Identity Provider;
2. пользователь входит на его странице;
3. приложение получает одноразовый authorization code;
4. code обменивается на токены с проверкой PKCE.

Не следует самостоятельно реализовывать протокол по отдельным HTTP-запросам. Лучше использовать официальную или поддерживаемую библиотеку выбранного провайдера. Устаревший Implicit Flow и OAuth Password Grant для новых приложений использовать не следует.

### Basic Auth

При Basic Auth логин и пароль передаются с каждым запросом в заголовке `Authorization`. Кодирование Base64 не является шифрованием, поэтому HTTPS обязателен. Для обычной SPA с пользовательским входом этот подход неудобен; чаще он встречается в небольших внутренних API и инструментах.

### API key

API key обычно идентифицирует приложение или технического клиента, а не пользователя. Секретный API key нельзя помещать в Vue-код или переменную `VITE_*`: всё, что попало в frontend-сборку, доступно пользователю. Запросы с секретным ключом должен выполнять backend.

## Краткий учебный вариант

Готовая реализация находится в [`vuejs/examples/posts`](../examples/posts/). Поток авторизации выглядит так:

```text
LoginModal → API-функция → Pinia auth store → запрос /users/me
                                      ↓
                         Router guard и интерфейс
```

Форма входа собирает credentials и отправляет событие родителю:

```vue
<script setup lang="ts">
import { reactive } from 'vue'

const emit = defineEmits<{
  submit: [credentials: { username: string; password: string }]
}>()

const form = reactive({ username: '', password: '' })

function submit() {
  emit('submit', {
    username: form.username.trim(),
    password: form.password,
  })
}
</script>

<template>
  <form @submit.prevent="submit">
    <input v-model="form.username" autocomplete="username" required>
    <input
      v-model="form.password"
      type="password"
      autocomplete="current-password"
      required
    >
    <button type="submit">Войти</button>
  </form>
</template>
```

В Pinia-store достаточно хранить `user`, `token`, `isLoading`, `error` и actions `login`, `logout`, `restoreSession`. Пароль в store сохранять нельзя. После входа store получает текущего пользователя, а при выходе или ответе `401` очищает локальное состояние.

Полезные файлы примера:

- [`LoginModal.vue`](../examples/posts/src/components/LoginModal.vue) — форма входа;
- [`api/auth.ts`](../examples/posts/src/api/auth.ts) — запросы авторизации;
- [`auth.store.ts`](../examples/posts/src/store/auth.store.ts) — состояние Pinia;
- [`routes.ts`](../examples/posts/src/routes.ts) — защита маршрутов.

Подробнее о полях формы: [Формы во Vue](forms.md).

## Хранение access token

В учебном варианте access token можно сохранить в `localStorage`, чтобы восстановить сессию после перезагрузки страницы:

```ts
// auth/token.ts
export const TOKEN_KEY = 'access_token'
```

```ts
// store/auth.store.ts
import { ref } from 'vue'
import { defineStore } from 'pinia'

import { getCurrentUser, login as loginRequest } from '@/api/auth'
import { TOKEN_KEY } from '@/auth/token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) ?? '')
  const user = ref(null)

  async function login(username: string, password: string) {
    const result = await loginRequest(username, password)

    token.value = result.access_token
    localStorage.setItem(TOKEN_KEY, token.value)
    user.value = await getCurrentUser()
  }

  async function restoreSession() {
    if (!token.value || user.value) return

    try {
      user.value = await getCurrentUser()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, user, login, logout, restoreSession }
})
```

Значение загружается из `localStorage` при создании store, записывается после успешного входа и удаляется при выходе. При восстановлении сессии одного наличия токена недостаточно: запрос `/users/me` проверяет, что backend принимает токен.

Это простой учебный вариант. Риски `localStorage` и предпочтительный production-подход описаны ниже в разделе [Хранение токенов в браузере](#хранение-токенов-в-браузере).

## Добавление токена в запросы

Чтобы не передавать токен вручную в каждой API-функции, общий Axios-клиент может добавлять заголовок через request interceptor:

```ts
// api/client.ts
import axios from 'axios'
import { TOKEN_KEY } from '@/auth/token'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})
```

Теперь защищённый запрос не содержит логику авторизации:

```ts
export async function getCurrentUser() {
  const response = await apiClient.get('/api/v1/users/me')
  return response.data
}
```

Interceptor выполняется перед каждым запросом и использует актуальное значение из хранилища. Заголовок добавляется только при наличии токена. Не добавляйте его к запросам на чужие домены: создавайте отдельный Axios-клиент для каждого внешнего API.

Константа `TOKEN_KEY` вынесена в независимый модуль, чтобы API-клиент не импортировал store. Иначе легко получить циклическую зависимость: store вызывает API, а API-клиент начинает импортировать store.

Если access token хранится только в памяти, вместо чтения `localStorage` interceptor должен получать его из отдельного модуля управления токеном.

### Вариант с `HttpOnly` cookie

При cookie-аутентификации frontend не читает токен и не формирует заголовок `Authorization`. Браузер добавляет cookie автоматически. Для cross-origin запросов Axios-клиенту нужен `withCredentials`:

```ts
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
})
```

Backend должен установить cookie и настроить разрешённый origin, credentials и защиту от CSRF. Значение `Access-Control-Allow-Origin: *` нельзя использовать вместе с credentialed-запросами.

## Защита маршрутов

Маршрут можно отметить полем `meta.requiresAuth` и проверить в navigation guard:

```ts
{
  path: '/profile',
  name: 'profile',
  component: () => import('@/views/ProfileView.vue'),
  meta: { requiresAuth: true },
}

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  await authStore.restoreSession()

  if (to.meta.requiresAuth && !authStore.user) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }
})
```

Guard защищает только переходы в интерфейсе. Пользователь может вызвать API напрямую, поэтому backend обязан проверять доступ к каждому закрытому endpoint.

Подробнее: [Meta-поля](router.md#meta-поля) и [Navigation guards](router.md#navigation-guards).

## Хранение токенов в браузере

Предпочтительный вариант для чувствительных production-приложений — серверная сессия или токены, недоступные JavaScript, в защищённых `HttpOnly` cookie. Access token иногда хранят только в памяти приложения.

`localStorage` упрощает учебный пример, но любой JavaScript того же origin может прочитать его содержимое. Одна XSS-уязвимость может раскрыть access token или refresh token. Поэтому нельзя автоматически переносить такую схему в production.

Независимо от подхода:

- используйте HTTPS;
- не храните и не логируйте пароль;
- ограничивайте срок жизни и права токенов;
- очищайте состояние при выходе и ответе `401`;
- проверяйте аутентификацию и права на backend;
- не считайте данные из Pinia или browser storage доверенными.
