# Debounce и throttle во Vue

`debounce` и `throttle` ограничивают частоту выполнения функции. Они полезны для событий, которые возникают много раз подряд: ввод текста, прокрутка, изменение размера окна и движение указателя.

| Техника | Когда выполняется функция | Типичный сценарий |
|---|---|---|
| Debounce | После паузы в серии событий | Поиск, автосохранение, валидация |
| Throttle | Не чаще одного раза за интервал | Scroll, resize, pointermove |
| `requestAnimationFrame` | Перед следующим кадром браузера | Визуальные обновления и анимация |

## Debounce

При каждом новом вызове debounce сбрасывает таймер. Функция выполнится только тогда, когда вызовы прекратятся на указанное время.

### `lodash.debounce`

[`lodash.debounce`](https://www.npmjs.com/package/lodash.debounce) — отдельный npm-пакет с готовой реализацией debounce из библиотеки Lodash. Он содержит только эту функцию, поэтому для неё не нужно подключать полный пакет `lodash`.

Установка:

```sh
npm install lodash.debounce
```

Простой пример:

```js
import debounce from 'lodash.debounce'

const search = debounce((query) => {
  console.log('Запрос:', query)
}, 300)

search('V')
search('Vu')
search('Vue')

// Через 300 мс выполнится только последний вызов: search('Vue').
```

Применение во Vue:

```vue
<script setup>
import { onBeforeUnmount } from 'vue'
import debounce from 'lodash.debounce'

async function loadProducts(query) {
  // Здесь выполняется запрос к API.
  console.log('Ищем:', query)
}

const debouncedSearch = debounce(loadProducts, 300)

onBeforeUnmount(() => {
  // Отменяем ожидающий вызов после удаления компонента.
  debouncedSearch.cancel()
})
</script>

<template>
  <input
    type="search"
    placeholder="Поиск"
    @input="debouncedSearch($event.target.value)"
  >
</template>
```

Обёрнутая функция предоставляет дополнительные методы:

```js
debouncedSearch.cancel() // Отменить ожидающий вызов.
debouncedSearch.flush()  // Выполнить ожидающий вызов немедленно.
```

Третий аргумент позволяет настроить `leading`, `trailing` и `maxWait`:

```js
const saveDraft = debounce(saveToApi, 500, {
  leading: false,
  trailing: true,
  maxWait: 3000,
})
```

### Самостоятельная реализация

Упрощённая версия помогает понять принцип работы debounce:

```js
export function debounce(callback, delay = 300) {
  let timeoutId

  function debounced(...args) {
    // Новый вызов отменяет предыдущий запланированный запуск.
    clearTimeout(timeoutId)

    timeoutId = setTimeout(() => {
      callback.apply(this, args)
    }, delay)
  }

  debounced.cancel = () => {
    clearTimeout(timeoutId)
  }

  return debounced
}
```

Например, API-поиск выполнится через 400 мс после окончания ввода:

```vue
<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { debounce } from '@/utils/debounce'

const search = ref('')
const results = ref([])

const searchProducts = debounce(async (query) => {
  // Пустую строку обрабатываем без запроса к серверу.
  if (!query.trim()) {
    results.value = []
    return
  }

  const response = await fetch(`/api/products?search=${encodeURIComponent(query)}`)
  results.value = await response.json()
}, 400)

// Не оставляем отложенный callback после удаления компонента.
onBeforeUnmount(() => searchProducts.cancel())
</script>

<template>
  <input
    v-model="search"
    type="search"
    placeholder="Поиск"
    @input="searchProducts(search)"
  >
</template>
```

## Debounce через `watch`

Во Vue таймер удобно создавать непосредственно внутри `watch`. Функция `onCleanup` отменяет предыдущий таймер перед повторным запуском watcher и при удалении компонента:

```vue
<script setup>
import { ref, watch } from 'vue'

const search = ref('')
const results = ref([])
const isLoading = ref(false)

watch(search, (query, _previousQuery, onCleanup) => {
  const controller = new AbortController()

  const timeoutId = setTimeout(async () => {
    if (!query.trim()) {
      results.value = []
      return
    }

    isLoading.value = true

    try {
      const response = await fetch(
        `/api/products?search=${encodeURIComponent(query)}`,
        { signal: controller.signal },
      )

      results.value = await response.json()
    } catch (error) {
      // AbortError ожидаем при появлении новой поисковой строки.
      if (error.name !== 'AbortError') throw error
    } finally {
      if (!controller.signal.aborted) isLoading.value = false
    }
  }, 400)

  onCleanup(() => {
    // Отменяем и ожидающий таймер, и уже начавшийся устаревший запрос.
    clearTimeout(timeoutId)
    controller.abort()
    isLoading.value = false
  })
})
</script>
```

Debounce уменьшает количество запросов, а `AbortController` не позволяет более старому запросу перезаписать результаты нового. Это разные задачи, поэтому для API-поиска их полезно применять вместе.

В Vue 3.5+ вместо третьего аргумента watcher также доступна функция `onWatcherCleanup()`. Её нужно вызывать синхронно, до первого `await`.

## Throttle

Throttle выполняет функцию сразу, а последующие события игнорирует до окончания интервала. Простая реализация:

```js
export function throttle(callback, delay = 200) {
  let isWaiting = false
  let timeoutId

  function throttled(...args) {
    // Пропускаем события, пока интервал ещё не закончился.
    if (isWaiting) return

    callback.apply(this, args)
    isWaiting = true

    timeoutId = setTimeout(() => {
      isWaiting = false
    }, delay)
  }

  throttled.cancel = () => {
    clearTimeout(timeoutId)
    isWaiting = false
  }

  return throttled
}
```

Пример обработки прокрутки:

```vue
<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { throttle } from '@/utils/throttle'

const scrollY = ref(0)

const updateScrollPosition = throttle(() => {
  scrollY.value = window.scrollY
}, 100)

onMounted(() => {
  window.addEventListener('scroll', updateScrollPosition, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateScrollPosition)
  updateScrollPosition.cancel()
})
</script>

<template>
  <p>Прокрутка: {{ scrollY }} px</p>
</template>
```

Эта реализация использует leading-вызов: первый вызов выполняется сразу. События внутри интервала отбрасываются. Более сложная реализация может поддерживать trailing-вызов — выполнение ещё одного callback с последними аргументами в конце интервала.

## Leading, trailing и `maxWait`

- `leading` выполняет callback в начале серии вызовов;
- `trailing` выполняет callback в конце серии;
- `maxWait` ограничивает максимальное время ожидания при непрерывных событиях.

Для кнопки обычно нужен leading-вызов, чтобы интерфейс реагировал сразу. Для поисковой строки чаще нужен trailing debounce. `maxWait` полезен для автосохранения: данные сохранятся даже при непрерывном вводе.

Самописные функции выше показывают основную механику. Если нужны все эти настройки, отмена и немедленное выполнение ожидающего callback, лучше использовать проверенную библиотеку.

## VueUse

VueUse предоставляет готовые функции и реактивные значения:

```sh
npm install @vueuse/core
```

Debounce реактивного значения:

```vue
<script setup>
import { ref, watch } from 'vue'
import { refDebounced } from '@vueuse/core'

const search = ref('')
const debouncedSearch = refDebounced(search, 400)

// Watcher сработает только после паузы во вводе.
watch(debouncedSearch, (query) => {
  loadProducts(query)
})
</script>

<template>
  <input v-model="search" type="search">
</template>
```

Ограничение частоты вызова функции:

```js
import { useDebounceFn, useThrottleFn } from '@vueuse/core'

const saveDraft = useDebounceFn(() => {
  // Выполняется после паузы, но не позднее чем через 3 секунды.
  saveToApi()
}, 500, { maxWait: 3000 })

const updatePosition = useThrottleFn(() => {
  // Выполняется не чаще одного раза за 100 мс.
  position.value = window.scrollY
}, 100)
```

Связанные возможности VueUse:

- `refDebounced` и `refThrottled` создают ограниченную по частоте версию `ref`;
- `watchDebounced` и `watchThrottled` применяют ограничение непосредственно к watcher;
- `useDebounceFn` и `useThrottleFn` оборачивают функцию;
- `useEventListener` автоматически удаляет DOM-обработчик при размонтировании компонента.

## `requestAnimationFrame`

Для изменений, связанных с отображением кадра, например перемещения элемента во время scroll, вместо таймера часто лучше использовать `requestAnimationFrame()`. Браузер вызовет callback перед следующей перерисовкой:

```js
let frameId = null

function handleScroll() {
  // В одном кадре планируется не более одного обновления.
  if (frameId !== null) return

  frameId = requestAnimationFrame(() => {
    updateVisualPosition(window.scrollY)
    frameId = null
  })
}

function cleanup() {
  if (frameId !== null) cancelAnimationFrame(frameId)
}
```

`requestAnimationFrame` синхронизирует работу с отрисовкой, но не заменяет debounce для API-запросов.

## Что выбрать

- Поиск по API — debounce 300–500 мс и отмена устаревшего запроса.
- Автосохранение — debounce с `maxWait`.
- Scroll и resize с расчётами — throttle.
- Изменение визуального положения элемента — `requestAnimationFrame`.
- Бесконечная прокрутка — по возможности `IntersectionObserver` вместо постоянного scroll-обработчика.
- Защита backend от нагрузки — серверные rate limits, кэширование и пагинация; frontend debounce их не заменяет.

Модификатор `v-model.lazy` не является debounce. Он обновляет значение по событию `change`, а не после паузы во вводе.

## Полезные ссылки

- [Очистка side effects в watcher](https://vuejs.org/guide/essentials/watchers.html#side-effect-cleanup)
- [`debounce` в документации Lodash](https://lodash.com/docs/#debounce)
- [`useDebounceFn` в VueUse](https://vueuse.org/shared/usedebouncefn/)
- [`useThrottleFn` в VueUse](https://vueuse.org/shared/usethrottlefn/)
- [`AbortController`](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [`requestAnimationFrame`](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
