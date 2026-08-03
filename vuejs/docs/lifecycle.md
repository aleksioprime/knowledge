# Жизненный цикл Vue

## Что такое жизненный цикл компонента

Жизненный цикл - это последовательность этапов от создания экземпляра компонента до его удаления. Vue сам проходит эти этапы, а lifecycle hooks позволяют запустить свой код в нужный момент.

Упрощённая последовательность выглядит так:

```text
инициализация
    ↓
beforeMount / onBeforeMount
    ↓
создание и вставка DOM
    ↓
mounted / onMounted
    ↓
изменилось реактивное состояние
    ↓
beforeUpdate / onBeforeUpdate
    ↓
обновление DOM
    ↓
updated / onUpdated
    ↓
beforeUnmount / onBeforeUnmount
    ↓
удаление DOM и остановка эффектов
    ↓
unmounted / onUnmounted
```

Этап обновления может повториться много раз. Этапы создания, монтирования и размонтирования для одного экземпляра компонента выполняются один раз.

## Options API и Composition API

Один и тот же этап называется по-разному в зависимости от используемого API:

| Этап | Options API | Composition API |
| --- | --- | --- |
| Начало инициализации | `beforeCreate` | код внутри `setup()` или `<script setup>` |
| Состояние и методы созданы | `created` | код внутри `setup()` или `<script setup>` |
| Перед первым рендерингом DOM | `beforeMount` | `onBeforeMount` |
| DOM компонента создан | `mounted` | `onMounted` |
| Перед обновлением DOM | `beforeUpdate` | `onBeforeUpdate` |
| DOM обновлён | `updated` | `onUpdated` |
| Перед удалением компонента | `beforeUnmount` | `onBeforeUnmount` |
| Компонент удалён | `unmounted` | `onUnmounted` |

В Composition API нет хуков `onBeforeCreate` и `onCreated`. Обычный код верхнего уровня `<script setup>` выполняется при настройке экземпляра компонента и заменяет большинство задач этих ранних хуков.

`setup()` выполняется раньше хуков Options API, включая `beforeCreate`. Не стоит смешивать два API без необходимости: для новых компонентов с `<script setup>` обычно используют функции `onMounted`, `onUpdated` и `onUnmounted`.

## Этапы подробнее

### 1. Инициализация

Vue создаёт экземпляр компонента, обрабатывает props и настраивает реактивное состояние, `computed`, методы и watchers.

В `<script setup>` этот код выполняется для каждого нового экземпляра компонента:

```vue
<script setup>
import { ref } from 'vue'

const count = ref(0)
console.log('Компонент инициализируется')
</script>
```

На этом этапе DOM компонента ещё не существует. Нельзя получить его элементы через template refs.

Обычно здесь создают состояние, настраивают `computed` и `watch`, а также могут запускать запросы, если для них не нужен DOM. Ждать `onMounted` только ради обычного HTTP-запроса необязательно.

В проектах с Vite шаблон `.vue`-компонента обычно компилируется во время сборки. Поэтому компиляцию шаблона не стоит воспринимать как обязательный отдельный этап при каждом создании компонента в браузере.

### 2. Первое отображение и монтирование

Перед первым отображением вызывается `onBeforeMount`. Реактивное состояние уже готово, но DOM-узлы компонента ещё не созданы.

После этого Vue создаёт DOM по шаблону и вставляет его в родительский контейнер. Затем вызывается `onMounted`.

```vue
<script setup>
import { ref, onBeforeMount, onMounted } from 'vue'

const inputRef = ref(null)

onBeforeMount(() => {
  console.log(inputRef.value) // null: input ещё не создан
})

onMounted(() => {
  console.log(inputRef.value) // HTMLInputElement
  inputRef.value.focus()
})
</script>

<template>
  <input ref="inputRef">
</template>
```

`onMounted` используют, когда нужен готовый DOM, browser API или библиотека, которая работает с DOM. Этот хук не выполняется во время серверного рендеринга.

### 3. Обновление

Если изменилось реактивное значение, используемое при рендеринге, Vue планирует обновление компонента. Несколько изменений состояния могут быть объединены в одно обновление DOM.

Порядок этапа:

1. Изменяется реактивное состояние.
2. Вызывается `onBeforeUpdate`.
3. Vue обновляет DOM.
4. Вызывается `onUpdated`.

```vue
<script setup>
import { ref, onBeforeUpdate, onUpdated } from 'vue'

const count = ref(0)

onBeforeUpdate(() => {
  console.log('DOM сейчас содержит старое значение')
})

onUpdated(() => {
  console.log('DOM уже содержит новое значение')
})
</script>

<template>
  <button @click="count++">Нажатий: {{ count }}</button>
</template>
```

Не изменяйте состояние компонента безусловно внутри `onUpdated`: это может запустить новое обновление и создать бесконечный цикл. Если нужно дождаться DOM после одного конкретного изменения, обычно понятнее использовать `nextTick()` рядом с этим изменением.

### 4. Размонтирование

Компонент размонтируется, когда Vue удаляет его из дерева, например из-за `v-if`, смены страницы или удаления родительского компонента.

`v-if="false"` действительно удаляет компонент и запускает его размонтирование. `v-show="false"` только скрывает DOM через CSS, поэтому lifecycle hooks размонтирования не вызываются.

Сначала вызывается `onBeforeUnmount`. Компонент и его DOM ещё доступны. После удаления DOM вызывается `onUnmounted`.

Во время размонтирования Vue автоматически останавливает реактивные эффекты компонента. Ресурсы, созданные вручную вне Vue, нужно очистить самостоятельно:

- таймеры и интервалы;
- глобальные DOM-события;
- `ResizeObserver`, `IntersectionObserver` и другие observers;
- WebSocket-соединения и сторонние подписки.

```vue
<script setup>
import { onMounted, onUnmounted } from 'vue'

const onResize = () => {
  console.log(window.innerWidth)
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>
```

Правило простое: если компонент что-то подключил или запустил вручную, при размонтировании он должен это отключить или остановить.

## Как регистрировать lifecycle hooks

Функции `onMounted`, `onUpdated` и другие Composition API hooks нужно регистрировать синхронно во время выполнения `setup()`:

```js
// Правильно
onMounted(() => {
  console.log('mounted')
})

// Неправильно: hook регистрируется слишком поздно
setTimeout(() => {
  onMounted(() => {
    console.log('не сработает как ожидается')
  })
}, 100)
```

Асинхронной может быть функция, переданная в hook, но сам вызов `onMounted(...)` должен произойти синхронно при настройке компонента.

## Когда какой hook нужен

- `onBeforeMount` - редко; DOM ещё не создан, но состояние уже настроено.
- `onMounted` - доступ к DOM, фокус, измерение размеров, browser API, запуск DOM-библиотеки.
- `onBeforeUpdate` - чтение состояния DOM непосредственно перед его обновлением.
- `onUpdated` - действие после любого обновления DOM компонента; для конкретного изменения часто лучше `nextTick`.
- `onBeforeUnmount` - действие непосредственно перед удалением, пока компонент ещё полностью доступен.
- `onUnmounted` - очистка таймеров, обработчиков, observers и внешних подписок.

## `watch()`

`watch()` следит за явно указанными реактивными данными и запускает callback, когда они изменились. Его используют для побочных действий: запросов, записи в `localStorage`, синхронизации со сторонними библиотеками и другой логики, которая не вычисляет значение для шаблона.

```vue
<script setup>
import { ref, watch } from 'vue'

const search = ref('')

watch(search, (newValue, oldValue) => {
  console.log('Поиск изменился:', oldValue, '->', newValue)
})
</script>
```

Callback получает новое значение, старое значение и функцию регистрации очистки:

```js
watch(source, (newValue, oldValue, onCleanup) => {
  // Побочное действие
}, options)
```

По умолчанию `watch` ленивый: при создании watcher callback не запускается, а ждёт первого изменения источника.

Источником может быть `ref`, `computed`, getter-функция, реактивный объект или массив из нескольких источников.

```js
const count = ref(0)

watch(count, (newCount, oldCount) => {
  console.log(oldCount, '->', newCount)
})
```

Передавать `.value` не нужно: `watch(count, ...)` получает сам `ref`, а Vue читает его значение автоматически.

Чтобы следить только за одним свойством реактивного объекта, передайте getter-функцию:

```js
const user = reactive({
  name: 'Анна',
  address: {
    city: 'Москва',
  },
})

watch(
  () => user.address.city,
  (newCity, oldCity) => {
    console.log(oldCity, '->', newCity)
  },
)
```

Так делать нельзя:

```js
watch(user.address.city, () => {})
```

В этом случае в `watch` попадёт текущее строковое значение, а не реактивный источник.

#### Несколько источников

```js
const page = ref(1)
const search = ref('')

watch(
  [page, search],
  ([newPage, newSearch], [oldPage, oldSearch]) => {
    console.log({ newPage, newSearch, oldPage, oldSearch })
  },
)
```

Также в массив можно добавлять getter-функции:

```js
watch([page, () => user.address.city], ([newPage, newCity]) => {
  console.log(newPage, newCity)
})
```

### `immediate`

Опция `immediate: true` запускает callback сразу при создании watcher, а затем при каждом изменении источника. При первом запуске `oldValue` равен `undefined`.

```js
watch(
  search,
  (newSearch, oldSearch) => {
    console.log({ newSearch, oldSearch })
    loadResults(newSearch)
  },
  { immediate: true },
)
```

Это удобно, когда одну и ту же функцию нужно использовать и для начальной загрузки, и для последующих обновлений.

### `once`

Опция `once: true` доступна с Vue 3.4. После первого вызова callback watcher автоматически останавливается.

```js
watch(
  isAuthorized,
  () => {
    console.log('Статус авторизации впервые изменился')
  },
  { once: true },
)
```

При совместном использовании `immediate: true` и `once: true` немедленный запуск считается первым: callback выполнится сразу, после чего watcher остановится.

### `deep`

Обычный watcher с getter следит за заменой возвращаемого значения, но не за изменением его вложенных свойств:

```js
watch(
  () => user.address,
  () => {
    console.log('Ссылка на address изменилась')
  },
)
```

Для отслеживания вложенных изменений используют `deep`:

```js
watch(
  () => user.address,
  (newAddress, oldAddress) => {
    console.log('Изменилось вложенное свойство address')
  },
  { deep: true },
)
```

При вложенном изменении `newAddress` и `oldAddress` могут ссылаться на один и тот же объект. Vue не создаёт его копию перед каждым обновлением.

Если передать в `watch` реактивный объект напрямую, глубокое отслеживание включится автоматически:

```js
watch(user, () => {
  console.log('Изменилось любое вложенное свойство user')
})
```

Глубокий обход большого объекта может быть дорогим. Если требуется одно поле, лучше следить за ним через getter. Начиная с Vue 3.5 вместо `true` можно передать максимальную глубину обхода, например `{ deep: 2 }`.

### Очистка предыдущего побочного эффекта

Если источник быстро меняется, предыдущий запрос может завершиться позже нового и записать устаревшие данные. `onWatcherCleanup` позволяет отменить работу перед повторным запуском watcher:

```vue
<script setup>
import { ref, watch, onWatcherCleanup } from 'vue'

const userId = ref(1)
const user = ref(null)

watch(userId, async (newUserId) => {
  const controller = new AbortController()

  onWatcherCleanup(() => {
    controller.abort()
  })

  const response = await fetch(`/api/users/${newUserId}`, {
    signal: controller.signal,
  })

  user.value = await response.json()
})
</script>
```

`onWatcherCleanup` доступен с Vue 3.5. Его нужно вызвать синхронно внутри callback, до первого `await`.

Универсальная альтернатива - третий аргумент callback `onCleanup`:

```js
watch(userId, async (newUserId, oldUserId, onCleanup) => {
  const controller = new AbortController()

  onCleanup(() => {
    controller.abort()
  })

  const response = await fetch(`/api/users/${newUserId}`, {
    signal: controller.signal,
  })
})
```

Функция очистки также вызывается при остановке watcher.

### Время запуска: `flush`

Vue группирует обновления, поэтому callback watcher не обязательно выполняется сразу после каждой строки с изменением состояния. Время запуска можно настроить:

- `flush: 'pre'` - значение по умолчанию; callback выполняется перед обновлением DOM текущего компонента;
- `flush: 'post'` - callback выполняется после обновления DOM и подходит для чтения обновлённых элементов;
- `flush: 'sync'` - callback выполняется сразу при изменении; не группируется и требует осторожности.

```js
watch(isOpen, () => {
  console.log('DOM уже обновлён')
}, { flush: 'post' })
```

`flush: 'sync'` не стоит использовать для массивов и других значений, которые могут много раз измениться в одном синхронном участке кода.

### Остановка, пауза и продолжение

`watch` возвращает управляющий объект-функцию. Методы `pause` и `resume` доступны в Vue 3.5+:

```js
const watcher = watch(search, loadResults)

watcher.pause()
watcher.resume()
watcher.stop()

// Вызов без метода также полностью останавливает watcher
watcher()
```

Watcher, созданный синхронно внутри `<script setup>`, Vue автоматически остановит при размонтировании компонента. Если создать его позже, например внутри `setTimeout`, связь с компонентом может потеряться — такой watcher нужно остановить вручную.

## `watchEffect()`

`watchEffect()` автоматически отслеживает все реактивные значения, которые были прочитаны внутри функции.

```vue
<script setup>
import { ref, watchEffect } from 'vue'

const count = ref(0)

watchEffect(() => {
  console.log('Текущее значение:', count.value)
})
</script>
```
