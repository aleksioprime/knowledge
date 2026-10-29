# Template refs и `useTemplateRef`

Template ref предоставляет прямой доступ к DOM-элементу или экземпляру дочернего компонента. Он нужен, например, чтобы установить фокус, измерить элемент, подключить `IntersectionObserver` или инициализировать стороннюю DOM-библиотеку.

Для обычного изменения интерфейса лучше использовать реактивные данные и шаблон Vue. Template refs стоит применять только там, где действительно нужен прямой доступ к элементу.

## `useTemplateRef` в Vue 3.5+

Начиная с Vue 3.5 рекомендуемый способ получить ссылку в Composition API — функция `useTemplateRef()`:

```vue
<script setup>
import { onMounted, useTemplateRef } from 'vue'

// Строка должна совпадать со значением ref в шаблоне.
const searchInput = useTemplateRef('search-input')

onMounted(() => {
  // DOM-элемент уже создан после монтирования компонента.
  searchInput.value?.focus()
})
</script>

<template>
  <input ref="search-input" type="search">
</template>
```

Имя JavaScript-переменной может быть любым. Связь с элементом задаёт строковый аргумент `useTemplateRef('search-input')`, который должен совпадать с `ref="search-input"`.

При использовании TypeScript редактор и `vue-tsc` обычно определяют тип элемента автоматически по шаблону.

## Когда значение доступно

До монтирования компонента `element.value` содержит `null`. Значение снова станет `null`, если элемент будет удалён, например директивой `v-if`. Поэтому при обращении к нему нужна проверка или optional chaining:

```js
element.value?.focus()
```

Если элемент появляется после изменения реактивного состояния, дождитесь обновления DOM через `nextTick()`:

```vue
<script setup>
import { nextTick, ref, useTemplateRef } from 'vue'

const isOpen = ref(false)
const input = useTemplateRef('input')

async function open() {
  isOpen.value = true

  // Vue применит v-if к DOM на следующем цикле обновления.
  await nextTick()
  input.value?.focus()
}
</script>

<template>
  <button type="button" @click="open">Открыть</button>
  <input v-if="isOpen" ref="input">
</template>
```

## Ссылка на компонент

Если `ref` установлен на компонент, значением будет его публичный экземпляр. Компоненты с `<script setup>` закрыты по умолчанию и явно публикуют доступные свойства и методы через `defineExpose()`:

```vue
<!-- SearchInput.vue -->
<script setup>
import { useTemplateRef } from 'vue'

const input = useTemplateRef('input')

function focus() {
  input.value?.focus()
}

// Родитель сможет вызвать только опубликованный метод focus.
defineExpose({ focus })
</script>

<template>
  <input ref="input" type="search">
</template>
```

```vue
<!-- Parent.vue -->
<script setup>
import { onMounted, useTemplateRef } from 'vue'
import SearchInput from './SearchInput.vue'

const search = useTemplateRef('search')

onMounted(() => search.value?.focus())
</script>

<template>
  <SearchInput ref="search" />
</template>
```

Для обычного взаимодействия родителя и ребёнка предпочтительнее `props` и события. Component ref используют, когда нужен императивный публичный метод вроде `focus()`.

## Template refs внутри `v-for`

В Vue 3.5+ один template ref внутри `v-for` содержит массив элементов:

```vue
<script setup>
import { onMounted, ref, useTemplateRef } from 'vue'

const items = ref(['Vue', 'Pinia', 'Vue Router'])
const itemElements = useTemplateRef('items')

onMounted(() => {
  console.log(itemElements.value)
})
</script>

<template>
  <ul>
    <li v-for="item in items" :key="item" ref="items">
      {{ item }}
    </li>
  </ul>
</template>
```

Порядок элементов в массиве template refs не гарантированно совпадает с порядком исходного массива. Не используйте индекс такого массива как устойчивый идентификатор элемента.

## Вариант до Vue 3.5

В Vue 3.4 и более ранних версиях template ref объявляют через обычный `ref(null)`. Имя переменной должно совпадать со значением атрибута в шаблоне:

```vue
<script setup>
import { onMounted, ref } from 'vue'

const input = ref(null)

onMounted(() => input.value?.focus())
</script>

<template>
  <input ref="input">
</template>
```

Обычный `ref()` продолжает работать и в новых версиях, но `useTemplateRef()` явно показывает назначение ссылки и улучшает автоматическое определение типов.

## Полезная ссылка

- [Template refs в официальной документации Vue](https://vuejs.org/guide/essentials/template-refs.html)
