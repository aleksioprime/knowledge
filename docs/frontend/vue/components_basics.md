# Основы работы с компонентами Vue

Карточка пользователя повторяется на пяти страницах, и каждая правка вёрстки расползается по всем копиям. Компонент собирает разметку, логику и стили в один файл, а props и события задают его контракт: что он принимает сверху и о чём сообщает родителю. Здесь — регистрация компонента, props, проваливание атрибутов, `emit` и `v-model`.

## Минимальный пример

```vue
<!-- TaskItem.vue -->
<script setup>
const props = defineProps({
  task: { type: Object, required: true },
})
const emit = defineEmits(['remove'])
</script>

<template>
  <li>
    {{ props.task.title }}
    <button @click="emit('remove', props.task.id)">Удалить</button>
  </li>
</template>
```

```vue
<!-- App.vue -->
<script setup>
import TaskItem from './TaskItem.vue'

function removeTask(id) {
  console.log('удалить задачу', id) // удалить задачу 1
}
</script>

<template>
  <ul>
    <TaskItem :task="{ id: 1, title: 'Купить хлеб' }" @remove="removeTask" />
  </ul>
</template>
```

## Как это работает

### Что такое компонент

Компонент Vue - это переиспользуемый блок интерфейса со своей разметкой, логикой и стилями.

Обычно компонент хранится в отдельном `.vue`-файле (SFC - Single File Component).

```vue
<template>
  <!-- Простая привязка переменной из script -->
  <button class="btn">{{ label }}</button>
</template>

<script setup>
// Локальное состояние компонента
const label = 'Нажми меня'
</script>

<style scoped>
.btn {
  padding: 8px 12px;
}
</style>
```

### Подключение компонента

#### Локальная регистрация

Компонент импортируется там, где используется

```vue
<script setup>
// Локальный импорт компонента для использования в шаблоне
import UserCard from './UserCard.vue'
</script>

<template>
  <UserCard />
</template>
```

### Передача данных через props

Родитель передает данные в дочерний компонент через атрибуты

#### Родитель

```vue
<template>
  <!-- Статическое имя и динамический числовой prop -->
  <UserCard name="Alex" :age="28" />
</template>
```

#### Дочерний компонент

```vue
<script setup>
// Описываем контракт входных данных компонента
const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  age: {
    type: Number,
    default: 0,
  },
})
</script>

<template>
  <!-- Используем входные данные из props -->
  <p>{{ props.name }} ({{ props.age }})</p>
</template>
```

- `props` идут только сверху вниз: от родителя к ребенку
- Не изменяйте `props` напрямую в дочернем компоненте, так как источник истины находится у родителя

#### Передача props из объекта

Если у вас есть объект `user`, есть несколько вариантов передать данные в компонент.

```vue
<script setup>
const user = {
  name: 'Alex',
  age: 28,
  role: 'admin',
}
</script>

<template>
  <!-- 1. Передаем конкретное поле явно -->
  <UserCard :name="user.name" />

  <!-- 2. Передаем объект целиком в prop user -->
  <UserCardWithObject :user="user" />

  <!-- 3. Разворачиваем объект в набор props через v-bind -->
  <UserCard v-bind="user" />
</template>
```

- Если компонент ожидает `name`, то безопасный вариант: `:name="user.name"`.
- Если компонент ожидает `user`, можно передать объект целиком и внутри обращаться к `props.user.name`.
- `v-bind="user"` разложит объект по prop-именам компонента. Если в объекте есть поля `name` и `age`, они попадут в props `name` и `age`.
- `v-bind` объекта удобен, когда имена полей объекта совпадают с именами props компонента.

#### Деструктуризация defineProps

`defineProps` можно деструктурировать, но здесь важно помнить про реактивность.

```vue
<script setup>
// Такой синтаксис возможен
const { title, count } = defineProps({
  title: String,
  count: Number,
})
</script>

<template>
  <h3>{{ title }}</h3>
  <p>{{ count }}</p>
</template>
```

- В новых версиях Vue с `<script setup>` деструктурированные `props` поддерживаются удобнее, но в старом коде это могло ломать реактивность.
- Самый безопасный и понятный вариант для учебного и командного кода: `const props = defineProps(...)` и доступ через `props.title`.
- Если нужно именно разложить `props` на отдельные реактивные переменные, обычно используют `toRefs(props)`.

#### Проваливание атрибутов в компонент (fall-through)

Не все атрибуты, переданные компоненту, обязаны быть объявлены как `props`.

Если атрибут или обработчик не описан в `props` и `emits`, Vue может автоматически "провалить" его на корневой DOM-элемент компонента.

#### Родитель

```vue
<template>
  <BaseButton class="primary" id="save-btn" @click="save" />
</template>
```

#### Дочерний компонент

```vue
<template>
  <button class="btn">Сохранить</button>
</template>
```

В результате `class`, `id` и обработчик `click` попадут на корневой `<button>` внутри `BaseButton`.

- это поведение называется fallthrough attributes
- часто так передают `class`, `style`, `id`, `disabled`, `data-*`, `aria-*`
- это удобно для оберток над обычными DOM-элементами: кнопками, инпутами, ссылками

#### Доступ к `$attrs`

Если нужно явно управлять такими атрибутами, используйте `$attrs` в шаблоне или `useAttrs()` в `<script setup>`.

```vue
<script setup>
import { useAttrs } from 'vue'

const attrs = useAttrs()
</script>

<template>
  <input class="input" v-bind="attrs" />
</template>
```

- `props` забирают только объявленные входные параметры компонента
- все остальные атрибуты и необъявленные обработчики попадают в `$attrs`
- `v-bind="attrs"` полезен, когда вы хотите пробросить атрибуты не в корень, а в конкретный элемент

#### Отключение автоматического проваливания

Автопроваливание работает особенно удобно у компонентов с одним корневым элементом.

Если у компонента несколько корневых узлов или вы хотите вручную контролировать, куда попадут атрибуты, обычно отключают автоматическое наследование и пробрасывают атрибуты явно.

```vue
<script setup>
defineOptions({
  inheritAttrs: false,
})
</script>

<template>
  <label class="field-label">Email</label>
  <input class="field-input" v-bind="$attrs" />
</template>
```

### Отправка событий в родителя (emit)

Чтобы дочерний компонент сообщил о действии, используйте событие

#### Дочерний компонент

```vue
<script setup>
// Объявляем события, которые компонент может отправлять наружу
const emit = defineEmits(['remove'])

function onRemove() {
  // Отправляем событие родителю
  emit('remove')
}
</script>

<template>
  <button @click="onRemove">Удалить</button>
</template>
```

#### Связь `$attrs` и `emits`

Здесь есть важная граница:

- объявленные `props` не попадают в `$attrs`
- события, объявленные через `emits`, тоже не считаются fallthrough-атрибутами
- в `$attrs` остаются только неописанные атрибуты и необъявленные обработчики

```vue
<script setup>
const emit = defineEmits(['click'])
</script>

<template>
  <button @click="emit('click')">Нажми</button>
</template>
```

Если родитель пишет `@click` на таком компоненте, это уже часть API компонента, а не обычный DOM-обработчик, который автоматически провалится вниз.

Это важно для базовых UI-компонентов: нужно явно решить, должен ли `click` быть собственным событием компонента через `emit`, или родитель должен просто передавать нативный обработчик на внутренний DOM-элемент через fallthrough.

#### Передача данных в emit (payload)

На практике чаще нужен не просто сигнал, а данные о событии

#### Дочерний компонент

```vue
<script setup>
// remove: действие, update:status: обновление конкретного поля
const emit = defineEmits(['remove', 'update:status'])

function onRemove(id) {
  // Передаем минимальный payload с контекстом
  emit('remove', { id, source: 'user-card' })
}

function onStatusChange(value) {
  // Для update-события обычно передается новое значение
  emit('update:status', value)
}
</script>

<template>
  <!-- Инициируем событие удаления -->
  <button @click="onRemove(42)">Удалить</button>
  <!-- Изменение статуса отправляем в родителя -->
  <select @change="onStatusChange($event.target.value)">
    <option value="active">active</option>
    <option value="archived">archived</option>
  </select>
</template>
```

#### Валидация emit

Если у события есть ожидаемая структура payload, ее можно описать в `defineEmits` через объект и функции-валидаторы.

```vue
<script setup>
const emit = defineEmits({
  remove: (payload) => {
    return typeof payload?.id === 'number'
  },
  'update:status': (value) => {
    return ['active', 'archived'].includes(value)
  },
})

function onRemove() {
  emit('remove', { id: 42 })
}

function onStatusChange(value) {
  emit('update:status', value)
}
</script>
```

- валидатор возвращает `true`, если payload корректный
- если вернуть `false`, Vue выдаст предупреждение в development-режиме
- это не замена бизнес-валидации, а способ явно описать контракт события
- особенно полезно, когда событие принимает объект или ограниченный набор значений

Практически это похоже на валидацию `props`: компонент документирует, какие события он отправляет и какие данные в них ожидаются.

#### Родитель

```vue
<template>
  <!-- с помощью remove получаем объект payload из emit('remove', payload) и -->
  <!-- $event содержит новое значение статуса -->
  <UserCard
    @remove="handleRemove"
    @update:status="status = $event"
  />
</template>

<script setup>
import { ref } from 'vue'

// Состояние на стороне родителя
const status = ref('active')

function handleRemove(payload) {
  // Достаем данные, пришедшие из дочернего emit
  console.log(payload.id, payload.source)
}
</script>
```

- Передавайте минимально необходимый payload.
- Для сложных событий лучше объект, чем длинный список аргументов.
- Названия событий делайте доменными: `save`, `remove`, `update:status`.

#### Родитель

```vue
<template>
  <!-- Родитель подписывается на событие дочернего компонента -->
  <UserCard @remove="handleRemove" />
</template>

<script setup>
function handleRemove() {
  console.log('Карточка удалена')
}
</script>
```

- `emit` используется для связи снизу вверх: от ребенка к родителю
- Имена событий в шаблоне принято писать в kebab-case
- Старайтесь не передавать в событии весь объект, если достаточно `id` и измененного поля

### v-model в компонентах

`v-model` в компоненте - это соглашение: `modelValue` как вход и `update:modelValue` как событие.

#### Дочерний компонент

```vue
<script setup>
// modelValue - стандартный вход для v-model в компоненте
const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})

// update:modelValue - стандартное событие для v-model
const emit = defineEmits(['update:modelValue'])

function onInput(event) {
  // Прокидываем новое значение в родителя
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <!-- Значение приходит из props, изменения уходят через emit -->
  <input :value="props.modelValue" @input="onInput" />
</template>
```

#### Родитель

```vue
<script setup>
import { ref } from 'vue'

// Локальное состояние родителя, синхронизированное с дочерним через v-model
const name = ref('')
</script>

<template>
  <!-- Короткая форма пары modelValue + update:modelValue -->
  <UserNameInput v-model="name" />
  <p>{{ name }}</p>
</template>
```

Для нескольких `v-model` используйте аргументы: `v-model:title`, `v-model:status` и события `update:title`, `update:status`.

### Лучшие практики child -> parent

- Используйте события как API компонента, а не прямой доступ к состоянию родителя.
- Стандартизируйте имена событий: действие (`save`, `remove`) или update-соглашение (`update:field`).
- Передавайте в `emit` только необходимый payload, избегайте избыточных данных.
- Валидацию и бизнес-логику оставляйте в родителе или в composable, а не в презентационном дочернем компоненте.
- Не злоупотребляйте цепочками `prop drilling` + `emit`; для глубоких деревьев используйте store или provide/inject.
- Документируйте `props` и `emits` как контракт компонента.

## Частые ошибки

- Изменение `props` напрямую внутри дочернего компонента (`props.name = ...`) → предупреждение в консоли, значение перезаписывается при следующем рендере родителя → хранить локальную копию в `ref` или отправлять `emit('update:...')` родителю.
- Отсутствие описания `props` и событий через `defineProps` и `defineEmits` → все атрибуты проваливаются в `$attrs`, обработчик `@remove` у родителя срабатывает не там или дважды, контракт компонента непонятен → объявлять каждый prop и событие явно и документировать их.
- Непрозрачный payload в `emit` (весь объект или несколько позиционных аргументов) → в обработчике родителя непонятно, что именно пришло, правки ломают оба компонента → передавать минимальный объект с понятными полями (`{ id, source }`).
- `v-model` на компоненте без пары `modelValue` + `update:modelValue` → поле не обновляется, родитель не видит ввод → соблюдать соглашение или задать имя через `v-model:title` и `update:title`.
- Один большой компонент на весь экран или глобальная регистрация всех компонентов без необходимости → файл на сотни строк, неочевидные зависимости, части нельзя переиспользовать → делить на подкомпоненты и импортировать локально там, где они нужны.

## Когда не использовать

Выделять компонент ради трёх строк разметки, которые встречаются один раз, не стоит: лишний файл и props усложняют чтение, ничего не экономя. Компонент окупается, когда разметка повторяется или у неё есть собственное состояние и поведение.

Цепочка `props` вниз и `emit` вверх через три-четыре уровня (prop drilling) — признак, что данные нужны не компонентам между ними: для общего состояния берите хранилище [Pinia](pinia.md) или `provide/inject`. А когда родитель хочет вставить в компонент свою разметку, а не данные, вместо props нужны [слоты](components_slots.md).

## Связанные темы

- [Slots в компонентах Vue](components_slots.md) — передача разметки вместо данных
- [События в Vue](events.md) — DOM-события в шаблоне и их модификаторы
- [Формы во Vue](forms.md) — `v-model` на обычных полях
- [Pinia: управление общим состоянием во Vue](pinia.md) — когда props и `emit` уже не хватает
- [Mixins и composables во Vue](mixins_composables.md)
