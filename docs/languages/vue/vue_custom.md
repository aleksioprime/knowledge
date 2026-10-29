# Пользовательские возможности Vue

В этом разделе будут собраны способы расширения стандартного поведения Vue: пользовательские директивы и другие связанные темы.

## Пользовательские директивы

Пользовательская директива позволяет переиспользовать логику, которая напрямую работает с DOM-элементом. Название директивы в шаблоне всегда начинается с `v-`.

Директиву стоит использовать для управления фокусом, выделения текста, обработки кликов вне элемента и похожих задач. Обычную логику приложения лучше выносить в компоненты или composables.

### Локальная директива

В `<script setup>` переменная с префиксом `v` автоматически становится доступна в шаблоне как директива. Например, `vFocus` превращается в `v-focus`:

```vue
<script setup>
const vFocus = {
  mounted(element) {
    element.focus()
  },
}
</script>

<template>
  <input v-focus>
</template>
```

Хук `mounted` выполняется после добавления элемента в DOM, поэтому в этот момент можно вызвать `focus()`.

### Значение директивы

Значение, переданное директиве, находится в `binding.value`. Предыдущее значение во время обновления доступно через `binding.oldValue`:

```vue
<script setup>
import { ref } from 'vue'

const color = ref('tomato')

const vColor = {
  mounted(element, binding) {
    element.style.color = binding.value
  },
  updated(element, binding) {
    element.style.color = binding.value
  },
}
</script>

<template>
  <p v-color="color">Цветной текст</p>
</template>
```

Если для `mounted` и `updated` нужна одинаковая логика, директиву можно записать одной функцией:

```js
const vColor = (element, binding) => {
  element.style.color = binding.value
}
```

### Аргументы и модификаторы

Директива может принимать аргумент и модификаторы:

```vue
<div v-example:tooltip.delay="message"></div>
```

В объекте `binding` будут доступны:

- `binding.value` — значение `message`;
- `binding.oldValue` — предыдущее значение;
- `binding.arg` — строка `'tooltip'`;
- `binding.modifiers` — объект `{ delay: true }`.

DOM-элемент `element` можно изменять, а свойства объекта `binding` следует считать доступными только для чтения.

### Хуки директивы

Объект директивы может содержать следующие хуки:

- `created` — директива создана, но атрибуты элемента ещё не применены;
- `beforeMount` — перед добавлением элемента в DOM;
- `mounted` — после добавления элемента в DOM;
- `beforeUpdate` — перед обновлением компонента;
- `updated` — после обновления компонента;
- `beforeUnmount` — перед удалением компонента;
- `unmounted` — после удаления компонента.

Обычно достаточно `mounted`, `updated` и `unmounted`. В `unmounted` нужно удалять добавленные обработчики событий и освобождать другие ресурсы.

### Глобальная директива

Если директива нужна во всём приложении, её можно зарегистрировать через `app.directive()` в `main.js`:

```js
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

app.directive('focus', {
  mounted(element) {
    element.focus()
  },
})

app.mount('#app')
```

После регистрации `v-focus` можно использовать в любом компоненте приложения.

Пользовательские директивы рекомендуется применять к обычным HTML-элементам. При использовании на компонентах директива применяется к корневому элементу компонента, а компонент с несколькими корневыми элементами может привести к предупреждению и неожиданному поведению.

## Provide и inject

`provide` и `inject` позволяют передавать данные от родительского компонента любому вложенному компоненту без последовательной передачи через `props` на каждом уровне.

### Props drilling

`Props drilling` — ситуация, когда данные приходится передавать через несколько уровней компонентов, хотя промежуточные компоненты сами их не используют:

```text
App → Layout → Sidebar → UserProfile
```

Например, значение `user` нужно только компоненту `UserProfile`, но `App` вынужден передать его в `Layout`, затем в `Sidebar` и только после этого в `UserProfile`. Чем глубже дерево, тем больше лишних `props` нужно объявлять и поддерживать.

`provide` позволяет предоставить значение один раз в `App`, а `inject` — получить его непосредственно в `UserProfile`. Промежуточные компоненты при этом ничего не передают. Для одного-двух уровней обычные `props` остаются более явным и предпочтительным решением.

Родительский компонент предоставляет значение с помощью `provide()`:

```vue
<!-- Parent.vue -->
<script setup>
import { provide } from 'vue'

provide('theme', 'dark')
</script>

<template>
  <Child />
</template>
```

Любой компонент ниже него в дереве получает значение через `inject()`:

```vue
<!-- Child.vue или более глубокий вложенный компонент -->
<script setup>
import { inject } from 'vue'

const theme = inject('theme')
</script>

<template>
  <p>Тема: {{ theme }}</p>
</template>
```

Первый аргумент обеих функций — общий ключ. Если несколько родительских компонентов предоставляют значение с одинаковым ключом, `inject()` получает значение от ближайшего родителя.

### Значение по умолчанию

Если провайдер может отсутствовать, вторым аргументом `inject()` передаётся значение по умолчанию:

```js
const theme = inject('theme', 'light')
```

Без провайдера и значения по умолчанию `inject()` вернёт `undefined` и Vue покажет предупреждение.

### Реактивные значения

Через `provide()` можно передавать `ref` и другие реактивные значения. Вложенный компонент получит тот же `ref`, поэтому изменения будут реактивными:

```vue
<!-- Provider.vue -->
<script setup>
import { provide, readonly, ref } from 'vue'

const count = ref(0)

function increment() {
  count.value++
}

provide('counter', {
  count: readonly(count),
  increment,
})
</script>
```

```vue
<!-- Consumer.vue -->
<script setup>
import { inject } from 'vue'

const { count, increment } = inject('counter')
</script>

<template>
  <button @click="increment">Счётчик: {{ count }}</button>
</template>
```

Изменять состояние рекомендуется в компоненте-провайдере. Для этого вместе с данными передаётся функция `increment`, а `readonly()` запрещает прямое изменение `count` в дочерних компонентах.

Переданный `ref` не разворачивается внутри `<script setup>`, поэтому там значение читается через `count.value`. В шаблоне Vue разворачивает его автоматически.

### Ключи Symbol

Строковые ключи удобны в небольших проектах. В большом приложении лучше использовать `Symbol`, чтобы разные провайдеры случайно не использовали одинаковое имя:

```js
// keys.js
export const counterKey = Symbol('counter')
```

```js
// Provider.vue
import { provide, ref } from 'vue'
import { counterKey } from './keys.js'

const counter = ref(0)
provide(counterKey, counter)
```

```js
// Consumer.vue
import { inject } from 'vue'
import { counterKey } from './keys.js'

const counter = inject(counterKey)
```

### Provide для всего приложения

Значение можно сделать доступным всем компонентам приложения через `app.provide()` в `main.js`:

```js
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

app.provide('apiUrl', 'https://api.example.com')
app.mount('#app')
```

`provide()` и `inject()` необходимо вызывать синхронно внутри `setup()` или `<script setup>`. Для обычной связи непосредственного родителя и ребёнка предпочтительнее использовать `props` и события. `provide`/`inject` полезны для глубоко вложенных компонентов, плагинов и общих зависимостей.
