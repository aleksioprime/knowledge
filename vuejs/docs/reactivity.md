# Реактивность в Vue

## Что такое реактивность

Реактивность в Vue - это механизм, при котором интерфейс автоматически обновляется, когда меняются данные.

Идея состоит в том, что имеется состояние, а шаблон или вычисления зависят от этого состояния Когда состояние меняется, Vue понимает это и обновляет связанные части интерфейса

## Что такое Proxy

`Proxy` - это встроенный объект JavaScript, который позволяет перехватывать операции над другим объектом.

Проще говоря, `Proxy` оборачивает объект и дает возможность отследить: чтение свойства, запись свойства, удаление свойства, проверку наличия ключа и другие операции

Упрощенный пример:

```js
const user = {
  name: 'Alex',
  age: 28,
}

const proxyUser = new Proxy(user, {
  get(target, key) {
    console.log('Чтение:', key)
    return target[key]
  },
  set(target, key, value) {
    console.log('Запись:', key, value)
    target[key] = value
    return true
  },
})


console.log(proxyUser.name) // Срабатывает `get`
proxyUser.age = 29 // Срабатывает `set`
```

Именно на этой идее Vue 3 строит реактивность для объектов

## `reactive()`

`reactive()` используют для объектов и массивов. Он создаёт Proxy-обертку, которая отслеживает, какие свойства были прочитаны, запоминает, какие части шаблона или вычислений зависят от этих свойств, и при изменении значения запускает повторный пересчет или обновление интерфейса

```vue
<script setup>
import { reactive } from 'vue'

const user = reactive({
  name: 'Alex',
  age: 28,
})

function birthday() {
  user.age += 1
}
</script>

<template>
  <p>{{ user.name }} - {{ user.age }}</p>
  <button @click="birthday">+1 год</button>
</template>
```

### Когда использовать `reactive`

`reactive` подходит, когда состояние естественно описывается объектом (форма, объект пользователя, набор фильтров, массив элементов и т.д.)

`reactive` не предназначен для испльзования с примитивами (`number`, `string`, `boolean`, `null`, `undefined`), так как он опирается на `Proxy`, а `Proxy` оборачивает именно объект.

```js
import { reactive, ref } from 'vue'

const state = reactive({ count: 0 })
const count = ref(0)

// Не тот случай, для примитивов reactive не используют
const wrong = reactive(0)
```

## `ref()`

`ref()` в основном используют для примитивов и одиночных значений. Он создает объект-обертку с полем `value`.

```vue
<script setup>
import { ref } from 'vue'

const count = ref(0)

function increment() {
  count.value++
}
</script>

<template>
  <p>{{ count }}</p>
  <button @click="increment">+</button>
</template>
```

В JavaScript значение хранится в `count.value`. В шаблоне Vue автоматически распаковывает `ref`, поэтому там пишут просто `count`

Но если передать в `ref` объект, логика остается той же. Но повсеместно так не делают, потому что для объектов и массивов `reactive()` часто удобнее по синтаксису.

Сравнение:

```js
const user1 = ref({ name: 'Alex', age: 28 })
user1.value.age++

const user2 = reactive({ name: 'Alex', age: 28 })
user2.age++
```

`ref` используют обычно для чисел, строк, булевых флагов, ссылок на DOM-элементы, значения, которое удобно хранить отдельно от объекта

Но `ref` нередко используют для объектов, когда значение часто заменяют целиком, например:

```js
const user = ref(null)

user.value = await fetchUser()
user.value = null
```

`ref` можно использовать не только как отдельную переменную, но и как значение свойства объекта.

```js
const state = {
  count: ref(0),
  title: ref('Vue'),
}

console.log(state.count.value)
state.count.value++
```

### `ref` внутри `reactive`

Это еще один важный сценарий: `ref` можно положить внутрь `reactive`-объекта.

```js
import { reactive, ref } from 'vue'

const state = reactive({
  count: ref(0),
})
```

В таком случае Vue автоматически распаковывает `ref` при доступе через свойство объекта:

```js
console.log(state.count) // 0

state.count = 5
console.log(state.count) // 5
```

Это удобно, когда вы хотите собрать состояние в один объект, но при этом использовать механизм `ref` на уровне отдельных полей.

### Важное исключение: массивы и коллекции

Для элементов массива и коллекций вроде `Map` автоматической распаковки нет.

```js
const list = reactive([ref('Vue')])

console.log(list[0].value)
```

То же касается, например, `Map`:

```js
const map = reactive(new Map([['count', ref(0)]]))

console.log(map.get('count').value)
```

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

## Потеря реактивности

Если вы достаете свойство из реактивного объекта в отдельную переменную, вы можете потерять реактивную связь.

```js
const user = reactive({
  name: 'Alex',
})

const name = user.name
```

После этого `name` - это просто текущее значение, а не реактивная ссылка на `user.name`.

Поэтому для `props` и реактивных объектов часто используют доступ через `user.name`, `toRefs(user)`, `toRef(user, 'name')`

Пример:

```js
import { reactive, toRefs } from 'vue'

const user = reactive({
  name: 'Alex',
  age: 28,
})

const { name, age } = toRefs(user)
```

## `computed()`

`computed()` используют для отслеживания зависимости и автоматического пересчёта значения во время смены реактивных данных внутри

```vue
<script setup>
import { ref, computed } from 'vue'

const firstName = ref('Alex')
const lastName = ref('Brown')

const fullName = computed(() => {
  return `${firstName.value} ${lastName.value}`
})
</script>

<template>
  <p>{{ fullName }}</p>
</template>
```

Если нужно не только читать вычисляемое значение, но и записывать его, можно передать объект.

```js
const firstName = ref('Alex')
const lastName = ref('Brown')

const fullName = computed({
  get() {
    return `${firstName.value} ${lastName.value}`
  },
  set(value) {
    const [first, last] = value.split(' ')
    firstName.value = first
    lastName.value = last
  },
})

fullName.value = 'Maria Green'
```

Такой `computed` называют writable computed: `get` возвращает вычисляемое значение, а `set` получает новое значение при записи. Это полезно, когда нужно связать одно вычисляемое поле с несколькими исходными значениями

В новых версиях Vue у геттера `computed` может быть доступ к предыдущему значению, но это более редкий и продвинутый сценарий.

```js
const count = ref(2)

const alwaysSmall = computed((previous) => {
  if (count.value <= 3) {
    return count.value
  }

  return previous
})
```

`computed` используют для отфильтрованных списков, форматированного текста, derived state вида `isValid`, `fullName`, `totalPrice`

`computed` не используют для побочных эффектов, сетевых запросов или записи данных.
