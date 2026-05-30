# Жизненный цикл Vue

## Что такое жизненный цикл компонента

Жизненный цикл компонента - это набор этапов, через которые проходит компонент:

- создание состояния
- рендер
- монтирование в DOM
- обновление при изменении данных
- удаление из DOM

Это важно, потому что разный код должен выполняться в разное время.

Например:

- запрос данных часто делают после монтирования
- работу с DOM делают, когда элемент уже появился
- очистку таймеров и подписок делают перед удалением компонента

## Основные lifecycle hooks

В Composition API чаще всего используют такие хуки:

- `onMounted`
- `onUpdated`
- `onUnmounted`
- `onBeforeMount`
- `onBeforeUpdate`
- `onBeforeUnmount`

Пример:

```vue
<script setup>
import { onMounted, onUnmounted } from 'vue'

function onResize() {
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

Здесь логика простая:

- после монтирования подписываемся на событие
- перед окончательным удалением компонента очищаем подписку

## Когда использовать хуки

- `onMounted` - когда нужно работать с DOM, запускать начальную загрузку данных, подключать внешние библиотеки
- `onUpdated` - когда нужно отреагировать на уже произошедшее обновление DOM
- `onUnmounted` - когда нужно очищать таймеры, события, подписки, observer-объекты

## `watch()`

`watch()` нужен, когда вы хотите отреагировать на изменение данных побочным действием.

```vue
<script setup>
import { ref, watch } from 'vue'

const search = ref('')

watch(search, (newValue, oldValue) => {
  console.log('Поиск изменился:', oldValue, '->', newValue)
})
</script>
```

Это уже не вычисление значения, а реакция на изменение.

### Типичные сценарии для `watch`

- запуск запроса при изменении фильтра
- синхронизация с `localStorage`
- реакция на изменение маршрута
- вызов стороннего API

### Когда `watch` особенно уместен

`watch` хорошо подходит, когда:

- нужно следить за конкретным источником
- важно получить старое и новое значение
- нужно контролировать момент запуска и побочный эффект

Пример:

```vue
<script setup>
import { ref, watch } from 'vue'

const page = ref(1)

watch(page, async (newPage) => {
  console.log('Загружаем страницу', newPage)
})
</script>
```

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

- `watchEffect` удобен для простых реактивных эффектов
- зависимости задаются не явно, а выводятся из кода внутри функции
- для более контролируемых сценариев часто удобнее обычный `watch`

## `computed` или `watch`

Разделение простое:

- `computed` - когда нужно получить новое значение из других значений
- `watch` - когда нужно выполнить действие при изменении

Пример:

- `fullName`, `filteredUsers`, `isFormValid` - это `computed`
- `saveToLocalStorage`, `fetchData`, `sendAnalytics` - это `watch`

## `nextTick()`

`nextTick()` используют, когда нужно дождаться, пока Vue применит изменения состояния к DOM.

Важно понимать: реактивные данные могут измениться сразу, но обновление DOM Vue обычно делает не мгновенно в ту же строку кода, а откладывает до ближайшего цикла обновления.

Поэтому такой код может сработать раньше, чем DOM реально обновится:

```js
count.value++
console.log(element.textContent)
```

Если после изменения состояния нужно, например, прочитать обновленный DOM, установить фокус, измерить размеры элемента или проскроллить к только что появившемуся блоку обычно используют `nextTick()`.

```vue
<script setup>
import { ref, nextTick } from 'vue'

const isOpen = ref(false)
// Ссылка на DOM-элемент input после его появления в шаблоне
const inputRef = ref(null)

async function open() {
  // Меняем состояние: после этого input должен появиться в DOM
  isOpen.value = true
  // Ждем, пока Vue завершит обновление DOM
  await nextTick()
  // Теперь элемент уже существует, и на него можно поставить фокус
  inputRef.value.focus()
}
</script>

<template>
  <button @click="open">Открыть</button>
  <!-- input появится только после isOpen = true -->
  <input v-if="isOpen" ref="inputRef" />
</template>
```

## События клавиатуры и lifecycle-сценарии

События клавиатуры технически относятся к событиям шаблона, но на практике часто связаны с жизненным циклом компонента и управлением фокусом.

Например:

- открыть модалку
- дождаться появления `input`
- поставить туда фокус
- закрыть модалку по `Escape`

```vue
<script setup>
import { ref, nextTick } from 'vue'

const isOpen = ref(false)
const inputRef = ref(null)

async function openModal() {
  isOpen.value = true
  await nextTick()
  inputRef.value.focus()
}

function closeModal() {
  isOpen.value = false
}
</script>

<template>
  <button @click="openModal">Открыть</button>

  <div v-if="isOpen" class="modal" @keydown.esc="closeModal">
    <input ref="inputRef" />
  </div>
</template>
```

Здесь сочетаются сразу несколько вещей:

- изменение состояния
- ожидание обновления DOM через `nextTick`
- работа с фокусом
- клавиатурное событие `@keydown.esc`

## Частые практические сценарии

### Загрузка данных после монтирования

```vue
<script setup>
import { ref, onMounted } from 'vue'

const users = ref([])

onMounted(async () => {
  // Здесь обычно делают первый запрос
  users.value = await fetchUsers()
})
</script>
```

### Очистка таймера

```vue
<script setup>
import { onMounted, onUnmounted } from 'vue'

let timerId = null

onMounted(() => {
  timerId = setInterval(() => {
    console.log('tick')
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timerId)
})
</script>
```

### Подписка на глобальное событие клавиатуры

```vue
<script setup>
import { onMounted, onUnmounted } from 'vue'

function onKeydown(event) {
  if (event.key === 'Escape') {
    console.log('Закрыть окно')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>
```

Это хороший пример кода, который обязательно требует очистки в `onUnmounted`.

## Краткое правило

- lifecycle hooks отвечают за момент выполнения кода в жизни компонента
- `watch` и `watchEffect` отвечают за реакцию на изменение данных
- `nextTick` нужен, когда вы ждете применения изменений к DOM
- события клавиатуры часто пересекаются с жизненным циклом, если есть управление фокусом, модалки, глобальные подписки и cleanup
