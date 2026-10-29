# Основы Vue.js

## Переменные и выражения в {{ }}

В шаблонах Vue можно выводить значения переменных и простых выражений через двойные фигурные скобки

```vue
<template>
  <h1>{{ title }}</h1>
  <p>{{ count + 1 }}</p>
  <p>{{ isReady ? 'Готово' : 'В процессе' }}</p>
  <p>{{ `Пользователь: ${userName}` }}</p>
</template>
```

В `{{ }}` можно использовать шаблонные строки с обратными кавычками и интерполяцией `${...}`.
Сложную логику лучше вынести в `computed`. Vue экранирует вывод, поэтому текст безопаснее, чем при `v-html`, но не может содержать форматирования

## Бинд атрибутов

Чтобы связать значение с атрибутом, используйте `v-bind:` или сокращение `:`.

```vue
<template>
  <img :src="imageUrl" :alt="imageAlt">
  <a :href="`/users/${userId}`" :class="{ active: isActive }">Профиль</a>
  <div :class="isError ? 'text-red' : 'text-green'">Статус</div>
  <div :class="{ active: isActive, disabled: isDisabled }">Кнопка</div>
  <div :class="['card', isHighlighted ? 'card--highlight' : '']">Карточка</div>
  <button :disabled="isSaving">Сохранить</button>
</template>
```

Биндинг позволяет динамически менять `src`, `href`, `class`, `style` и другие атрибуты. В выражении биндинга можно использовать тернарный оператор `? :` для условного значения. В биндинге можно собирать строки через шаблонные строки с ${...}. Для `class` тернарный оператор удобно использовать, когда нужно выбрать один из двух CSS-классов, объект - если нужно включать и выключать несколько классов по условиям, и массив - если нужно собрать базовый класс и условные добавки.

### Динамические стили

Директива `:style` позволяет менять CSS-свойства в зависимости от состояния компонента. Ей можно передать объект или массив объектов:

```vue
<script setup>
import { computed, ref } from 'vue'

const isError = ref(false)
const fontSize = ref(18)
const baseStyle = { padding: '12px' }

const textStyle = computed(() => ({
  color: isError.value ? 'crimson' : 'green',
  fontSize: `${fontSize.value}px`,
}))
</script>

<template>
  <p :style="[baseStyle, textStyle]">Статус</p>
  <div :style="{ opacity: isError ? 0.5 : 1 }">Содержимое</div>
</template>
```

Названия CSS-свойств можно записывать в `camelCase` (`fontSize`) или в кавычках через дефис (`'font-size'`). Для свойств с единицами измерения их нужно указывать явно: `` `${fontSize}px` ``. Если динамически меняется только внешний вид состояния, чаще удобнее использовать `:class`, а `:style` оставлять для вычисляемых значений.

## Поля ввода и `v-model`

### Ручная реализация для обычного `input`

Чтобы связать поле ввода с реактивной переменной вручную, нужно передать значение через `:value` и обновлять переменную по событию `input`:

```vue
<script setup>
import { ref } from 'vue'

const temperature = ref(null)

const inputTemperature = (event) => {
  const value = event.target.value
  temperature.value = value === '' ? null : Number(value)
}
</script>

<template>
  <input
    type="number"
    :value="temperature"
    @input="inputTemperature"
  >

  <p>Температура: {{ temperature }}</p>
</template>
```

Проверка на пустую строку важна: `Number('')` возвращает `0`, хотя пользователь ничего не ввёл.

### `v-model` для обычного `input`

`v-model` сокращает связывание `:value` и `@input` до одной директивы:

```vue
<script setup>
import { ref } from 'vue'

const temperature = ref(null)
</script>

<template>
  <input v-model.number="temperature" type="number">
  <p>Температура: {{ temperature }}</p>
</template>
```

`v-model` создаёт двустороннюю связь: изменение поля обновляет переменную, а изменение переменной обновляет поле.

Основные модификаторы:

- `.number` - преобразует введённое значение в число, если это возможно. Для `input type="number"` применяется автоматически. Пустое поле возвращает пустую строку.
- `.trim` - удаляет пробелы в начале и конце строки.
- `.lazy` - обновляет значение по событию `change`, а не после каждого `input`.

```vue
<input v-model.trim="name" type="text">
<input v-model.lazy="comment" type="text">
```

### Наивная реализация `v-model` в своём компоненте

Без `defineModel` компонент поля принимает prop `modelValue` и отправляет новое значение событием `update:modelValue`:

```vue
<!-- Input.vue -->
<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const inputValue = (event) => {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <input
    type="text"
    :value="props.modelValue"
    @input="inputValue"
  >
</template>
```

Родитель использует этот компонент как обычное поле:

```vue
<script setup>
import { ref } from 'vue'
import Input from './Input.vue'

const name = ref('')
</script>

<template>
  <Input v-model="name" />
</template>
```

Vue преобразует `v-model="name"` примерно в такую запись:

```vue
<Input
  :model-value="name"
  @update:model-value="name = $event"
/>
```

Событие с произвольным именем, например `input`, само по себе не создаёт `v-model`: для модели без имени нужны именно `modelValue` и `update:modelValue`.

### `defineModel`

Начиная с Vue 3.4 ручное объявление prop и события можно заменить макросом `defineModel`:

```vue
<!-- Input.vue -->
<script setup>
const model = defineModel({
  type: String,
  required: true,
})
</script>

<template>
  <input v-model="model" type="text">
</template>
```

`defineModel()` возвращает `ref`. Чтение выполняется через `model.value`, а присваивание нового значения автоматически отправляет событие обновления родителю.

Варианты вызова:

```js
// modelValue + update:modelValue
const model = defineModel()

// modelValue с настройками prop
const model = defineModel({
  type: String,
  default: '',
  validator: (value) => value.length <= 100,
})

// Именованная модель title + update:title
const title = defineModel('title')

// Именованная модель с настройками
const title = defineModel('title', {
  type: String,
  required: true,
})
```

Основные параметры `defineModel`:

- первый строковый аргумент - имя модели; без него используется `modelValue`;
- `type` - ожидаемый тип значения;
- `required` - обязательна ли модель со стороны родителя;
- `default` - значение по умолчанию;
- `validator` - функция дополнительной проверки;
- `get` и `set` - функции преобразования значения при чтении и записи.

С `default` нужно быть осторожным: если родитель не передал значение, у дочернего компонента уже может быть значение по умолчанию, а у переменной родителя останется `undefined`. Лучше инициализировать связанную переменную в родителе.

### Именованный и множественный `v-model`

Аргумент после двоеточия - это имя модели компонента, а выражение справа - переменная родителя:

```vue
<!-- Родитель -->
<UserName
  v-model:first-name="firstName"
  v-model:last-name="lastName"
/>
```

```vue
<!-- UserName.vue -->
<script setup>
const firstName = defineModel('firstName', { required: true })
const lastName = defineModel('lastName', { required: true })
</script>

<template>
  <input v-model="firstName" type="text">
  <input v-model="lastName" type="text">
</template>
```

Один компонент может иметь несколько независимых `v-model`. В ручной реализации им соответствуют props `firstName`, `lastName` и события `update:firstName`, `update:lastName`.

### Пользовательские модификаторы

Модификаторы компонента доступны вторым элементом результата `defineModel`. Значение можно преобразовать через `get` или `set`:

```vue
<!-- Родитель: <Input v-model.capitalize="name" /> -->
<script setup>
const [model, modifiers] = defineModel({
  set(value) {
    if (modifiers.capitalize && value) {
      return value[0].toUpperCase() + value.slice(1)
    }

    return value
  },
})
</script>

<template>
  <input v-model="model" type="text">
</template>
```

Для именованной модели синтаксис можно комбинировать: `v-model:title.capitalize="title"`.

## Условия

Для условного отображения используется `v-if`, `v-else-if` и `v-else`. Они добавляют и удаляют элементы из DOM по условию. Должны располагаться на одном уровне вложенности

```vue
<template>
  <p v-if="status === 'loading'">Загрузка...</p>
  <p v-else-if="status === 'error'">Ошибка</p>
  <p v-else>Данные загружены</p>
</template>
```

Если блок переключается часто, иногда удобнее `v-show`.

```vue
<template>
  <p v-show="isVisible">Этот текст можно скрывать без удаления из DOM</p>
</template>
```

`v-show` не удаляет элемент из DOM, а переключает его видимость через CSS `display`. Это удобно, когда элемент часто показывается и скрывается, например для dropdown, tooltip, tabs или простого блока с деталями. У `v-show` нет пары `v-else` и `v-else-if`.

## Циклы

Для вывода списков используется `v-for`.

```vue
<template>
  <ul>
    <li v-for="(item, index) in items" :key="item.id">
      {{index + 1}}. {{ item.name }}
    </li>
  </ul>
</template>
```

`:key` нужен Vue, чтобы однозначно отличать элементы списка друг от друга. При добавлении, удалении или изменении порядка элементов Vue по ключу понимает, какой DOM-элемент нужно обновить, переместить или удалить. Это помогает сохранить правильное состояние элементов и компонентов, например значение поля ввода.

В качестве `:key` указывайте уникальный и стабильный идентификатор, который принадлежит самому элементу, например `item.id`. Индекс массива (`:key="index"`) обычно не подходит: после сортировки или удаления индекс может перейти к другому элементу, из-за чего Vue переиспользует неверный DOM-элемент. Индекс допустим только для статичного списка, порядок и состав которого не меняются.
