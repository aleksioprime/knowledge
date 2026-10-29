# Template refs и `useTemplateRef`

Реактивных данных и шаблона иногда не хватает: после открытия формы нужно поставить курсор в поле, измерить высоту блока, подключить `IntersectionObserver` или передать элемент сторонней DOM-библиотеке. Для таких случаев Vue даёт ссылку на шаблон (template ref) — прямой доступ к DOM-элементу или экземпляру дочернего компонента.

Для обычного изменения интерфейса лучше использовать реактивные данные и шаблон Vue. Template refs стоит применять только там, где действительно нужен прямой доступ к элементу.

## Минимальный пример

```vue
<script setup>
import { onMounted, useTemplateRef } from 'vue'

const titleInput = useTemplateRef('title-input')

onMounted(() => {
  titleInput.value?.focus()
  console.log(titleInput.value.tagName) // INPUT
})
</script>

<template>
  <input ref="title-input" placeholder="Название задачи">
</template>
```

## Как это работает

### `useTemplateRef` в Vue 3.5+

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

### Когда значение доступно

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

### Ссылка на компонент

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

### Template refs внутри `v-for`

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

### Вариант до Vue 3.5

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

### Полезная ссылка

- [Template refs в официальной документации Vue](https://vuejs.org/guide/essentials/template-refs.html)

## Частые ошибки

- Обращение к ссылке прямо в `<script setup>`, до монтирования → `input.value` равен `null`, при вызове метода выходит `TypeError: Cannot read properties of null` → читать значение в `onMounted` или в обработчике события и использовать `?.`.
- Строка в `useTemplateRef('input')` не совпадает с атрибутом `ref="search-input"` → значение всегда `null`, хотя элемент на странице есть → сверить имя в шаблоне и в вызове `useTemplateRef`.
- Фокус ставится сразу после `isOpen.value = true`, а элемент под `v-if` → DOM ещё не обновлён, ссылка пуста → дождаться `await nextTick()` и только потом обращаться к элементу.
- Родитель вызывает метод дочернего компонента, который не опубликован через `defineExpose` → `search.value.focus is not a function` → перечислить нужные методы в `defineExpose({ focus })`.
- Индекс массива ссылок внутри `v-for` используется как идентификатор элемента → после перерисовки элемент «съезжает» на соседний → хранить идентификатор в данных и искать элемент по нему.

## Когда не использовать

Если нужно показать или скрыть блок, добавить класс, поменять текст или значение поля, template ref лишний: это делают реактивные данные, `v-if`, `:class` и `v-model`. Прямое изменение DOM через ссылку Vue не отслеживает, и при следующей перерисовке результат может быть перезаписан.

Для передачи данных между родителем и дочерним компонентом ссылки на компонент тоже не подходят: такой код связывает компоненты внутренними деталями. Берите `props` для данных вниз и события для сообщений вверх, а ссылку на компонент оставьте для редких императивных команд вроде `focus()` или `scrollIntoView()`.

## Связанные темы

- [Жизненный цикл Vue](lifecycle.md) — `onMounted`, после которого доступен DOM
- [Реактивность в Vue](reactivity.md) — `ref` и `nextTick`
- [Основы работы с компонентами Vue](components_basics.md) — `props`, события и `defineExpose`
- [Teleport во Vue](teleport.md) — перенос части шаблона в другой DOM-элемент
