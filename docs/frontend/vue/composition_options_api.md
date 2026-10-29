# Composition API и Options API

Один и тот же компонент можно написать двумя способами: разложить код по опциям `data`, `methods`, `computed` или собрать его по смыслу через `ref` и `computed` внутри `<script setup>`. Пока компонент маленький, разницы почти нет, но когда в нём десять полей состояния и логика фильтра перемешана с логикой загрузки, выбор стиля определяет, насколько легко будет читать и переиспользовать код. Здесь — чем отличаются Options API и Composition API и как выбирать между ними.

## Минимальный пример

```vue
<script setup>
import { computed, ref } from 'vue'

const tasks = ref([
  { id: 1, title: 'Купить хлеб', done: true },
  { id: 2, title: 'Написать отчёт', done: false },
])
const doneCount = computed(() => tasks.value.filter((task) => task.done).length)
</script>

<template>
  <p>Выполнено: {{ doneCount }} из {{ tasks.length }}</p>
  <!-- Выполнено: 1 из 2 -->
  <label v-for="task in tasks" :key="task.id">
    <input type="checkbox" :checked="task.done" @change="task.done = !task.done">
    {{ task.title }}
  </label>
</template>
```

## Как это работает

В Vue 3 доступны два основных способа писать компонентную логику: `Options API` и `Composition API`. Оба подхода работают вместе, но подходят для разных задач и стиля кода.

### Options API

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

### Composition API

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

### Когда выбирать

- Используйте `Options API`, если нужен простой и знакомый стиль для небольших компонентов.
- Используйте `Composition API`, если логика сложная, её нужно переиспользовать или удобно группировать по смыслу.
- В одном проекте можно смешивать оба подхода, но лучше придерживаться единого стиля в пределах компонента.

### Коротко

- `Options API` - код организован по опциям компонента.
- `Composition API` - код организован по логике и функциям.
- Оба подхода поддерживаются Vue 3.

## Частые ошибки

- В Composition API `ref` читается без `.value` внутри `<script setup>` (`count + 1` вместо `count.value + 1`) → в вычислениях получается `[object Object]1` или `NaN`, хотя в шаблоне значение отображается верно → в скрипте обращаться через `.value`; в шаблоне Vue разворачивает `ref` сам.
- В Options API метод или обработчик `watch` записан стрелочной функцией → `this` равен `undefined`, состояние не меняется → писать обычные методы (`increment() {}`), стрелки оставлять для колбэков внутри них.
- Два API смешаны в одном компоненте: часть состояния в `data()`, часть в `<script setup>` → непонятно, где искать поле, `this` в одном месте работает, в другом нет → выбрать один стиль на компонент.
- Вся логика Composition API свалена в один длинный `<script setup>` без группировки → такой компонент читается хуже, чем тот же код на Options API → группировать код по задачам и выносить повторяющиеся части в composables.
- Логика Options API переиспользуется через миксины → неясно, откуда пришло поле, конфликты имён между миксинами → в новом коде брать composables.

## Когда не использовать

Переписывать рабочий компонент с Options API на Composition API только ради единообразия не стоит: поведение не изменится, а риск ошибки есть. Миграцию имеет смысл делать вместе с другой правкой компонента или когда его логику нужно вынести в composable.

Composition API не нужен для простого компонента с парой полей и одним методом — Options API читается там ничуть не хуже. И наоборот: если в проекте принят `<script setup>`, новый компонент на Options API будет выглядеть чужеродно, даже если он маленький.

## Связанные темы

- [Реактивность в Vue](reactivity.md) — `ref`, `reactive` и `computed`, на которых строится Composition API
- [Жизненный цикл Vue](lifecycle.md) — имена хуков в обоих API
- [Mixins и composables во Vue](mixins_composables.md) — переиспользование логики в каждом из подходов
- [Основы Vue.js](vue_basics.md)
