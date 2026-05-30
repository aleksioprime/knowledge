# Composition API и Options API

В Vue 3 доступны два основных способа писать компонентную логику: `Options API` и `Composition API`. Оба подхода работают вместе, но подходят для разных задач и стиля кода.

## Options API

`Options API` группирует код по разделам: `data`, `methods`, `computed`, `watch`, `mounted`.

```vue
<script>
export default {
  data() {
    return {
      count: 0,
    }
  },
  computed: {
    doubleCount() {
      return this.count * 2
    },
  },
  methods: {
    increment() {
      this.count += 1
    },
  },
}
</script>

<template>
  <button @click="increment">{{ count }} / {{ doubleCount }}</button>
</template>
```

- Подходит для небольших и средних компонентов.
- Логика разделена по типам опций, поэтому её проще читать новичкам.
- `this` используется внутри методов и вычисляемых свойств.

## Composition API

`Composition API` группирует код по смыслу. Обычно его пишут внутри `setup()` или через `<script setup>`.

```vue
<script setup>
import { computed, ref } from 'vue'

const count = ref(0)
const doubleCount = computed(() => count.value * 2)

function increment() {
  count.value += 1
}
</script>

<template>
  <button @click="increment">{{ count }} / {{ doubleCount }}</button>
</template>
```

- Удобен для переиспользования логики через composables.
- Лучше подходит для крупных компонентов и сложных сценариев.
- Не требует `this`: работа идет через `ref`, `computed` и другие функции Vue.

## Когда выбирать

- Используйте `Options API`, если нужен простой и знакомый стиль для небольших компонентов.
- Используйте `Composition API`, если логика сложная, её нужно переиспользовать или удобно группировать по смыслу.
- В одном проекте можно смешивать оба подхода, но лучше придерживаться единого стиля в пределах компонента.

## Коротко

- `Options API` - код организован по опциям компонента.
- `Composition API` - код организован по логике и функциям.
- Оба подхода поддерживаются Vue 3.