# Mixins и composables во Vue

Пагинация, отслеживание курсора, флаги загрузки — одна и та же логика нужна в десятке компонентов, а копировать `data`, `methods` и обработчики в каждый — значит править их потом в десяти местах. Во Vue для этого два механизма: примесь (mixin) для Options API и composable-функция для Composition API. Здесь — как работают оба, почему mixins для нового кода не рекомендуются и как перенести mixin в composable.

## Минимальный пример

Composable — обычная функция, которая создаёт реактивное состояние и возвращает его. Каждый вызов даёт независимую копию.

```vue
<script setup>
import { computed, ref } from 'vue'

function useTaskList(initial = []) {
  const tasks = ref(initial)
  const doneCount = computed(() => tasks.value.filter((task) => task.done).length)
  function toggle(task) {
    task.done = !task.done
  }
  return { tasks, doneCount, toggle }
}

const { tasks, doneCount, toggle } = useTaskList([{ id: 1, title: 'Купить хлеб', done: false }])
</script>

<template>
  <p>Выполнено: {{ doneCount }} из {{ tasks.length }}</p>  <!-- 0 из 1, после клика 1 из 1 -->
  <label v-for="task in tasks" :key="task.id">
    <input type="checkbox" :checked="task.done" @change="toggle(task)"> {{ task.title }}
  </label>
</template>
```

## Как это работает

Mixin — объект с опциями компонента, который позволяет повторно использовать `data`, `computed`, `methods`, watchers и lifecycle hooks в компонентах Options API.

Mixins продолжают поддерживаться в Vue 3, но для нового кода не рекомендуются. Основной современный способ повторного использования логики — composable-функции на базе Composition API.

### Локальный mixin

Mixin описывается как обычный объект с опциями компонента:

```js
// mixins/mouseMixin.js
export const mouseMixin = {
  data() {
    return {
      mouseX: 0,
      mouseY: 0,
    }
  },

  mounted() {
    // Подписываемся при монтировании использующего mixin компонента.
    window.addEventListener('mousemove', this.updateMousePosition)
  },

  beforeUnmount() {
    // Каждый side effect должен иметь симметричную очистку.
    window.removeEventListener('mousemove', this.updateMousePosition)
  },

  methods: {
    updateMousePosition(event) {
      this.mouseX = event.pageX
      this.mouseY = event.pageY
    },
  },
}
```

Компонент подключает один или несколько mixins через массив `mixins`:

```vue
<script>
import { mouseMixin } from '@/mixins/mouseMixin'

export default {
  mixins: [mouseMixin],

  mounted() {
    // Свойства mixin становятся частью this компонента.
    console.log(this.mouseX, this.mouseY)
  },
}
</script>

<template>
  <p>Координаты: {{ mouseX }}, {{ mouseY }}</p>
</template>
```

Из шаблона не видно, что `mouseX`, `mouseY` и `updateMousePosition` появились из `mouseMixin`. Это одна из причин, по которой большой компонент с несколькими mixins сложно читать.

### Правила объединения

Vue объединяет опции mixin с опциями компонента:

- lifecycle hooks mixin и компонента выполняются оба;
- hook mixin выполняется раньше одноимённого hook компонента;
- объектные опции, например `methods` и `computed`, объединяются;
- при конфликте одинаковых имён приоритет имеет опция самого компонента;
- несколько mixins применяются в порядке, указанном в массиве.

```js
const exampleMixin = {
  created() {
    console.log('mixin')
  },
  methods: {
    save() {
      console.log('save from mixin')
    },
  },
}

export default {
  mixins: [exampleMixin],
  created() {
    // Сначала выведется «mixin», затем «component».
    console.log('component')
  },
  methods: {
    // Метод компонента заменит одноимённый метод mixin.
    save() {
      console.log('save from component')
    },
  },
}
```

Не стоит рассчитывать на неявное переопределение как на основной механизм расширения: оно усложняет поиск фактической реализации метода.

### Проблемы mixins

#### Неясный источник свойств

По коду компонента трудно понять, какой mixin добавил `loading`, `error` или `loadData`. Для поиска определения приходится изучать все подключённые mixins.

#### Конфликты имён

Два mixins могут определить одноимённые свойства:

```js
export const paginationMixin = {
  data: () => ({ loading: false }),
}

export const searchMixin = {
  // Имя loading конфликтует с paginationMixin.
  data: () => ({ loading: false }),
}
```

#### Неявные зависимости

Один mixin может обращаться к свойству или методу, который должен предоставить компонент или другой mixin. Такая связь не выражена аргументами и легко ломается при рефакторинге.

#### Сложности типизации

Свойства разных mixins объединяются в `this` динамически. TypeScript сложнее вывести такой составной тип, особенно при конфликтах и глобальных mixins.

### Глобальный mixin

`app.mixin()` применяет mixin ко всем компонентам приложения:

```js
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

app.mixin({
  created() {
    // Этот hook выполнится для каждого компонента приложения.
    console.log('Создан компонент:', this.$options.name)
  },
})

app.mount('#app')
```

Глобальные mixins влияют даже на компоненты, которым эта логика не нужна, усложняют тестирование и могут ухудшить производительность. В коде приложения их следует избегать. Для явного подключения возможностей используйте composables, plugins или `app.provide()`.

### `extends`

Опция `extends` позволяет Options API-компоненту наследовать опции одного базового компонента:

```js
import BaseList from './BaseList.js'

export default {
  extends: BaseList,
  // Опции текущего компонента дополняют или переопределяют BaseList.
}
```

`extends` выражает наследование, а `mixins` — добавление нескольких фрагментов поведения. Оба механизма используют похожие правила объединения и не рекомендуются для Composition API. Обычно общую логику лучше вынести в composable, а общий интерфейс — в компонент.

### Замена mixin на composable

Та же логика координат мыши в современном варианте:

```js
// composables/useMouse.js
import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useMouse() {
  const x = ref(0)
  const y = ref(0)

  function update(event) {
    x.value = event.pageX
    y.value = event.pageY
  }

  onMounted(() => {
    window.addEventListener('mousemove', update)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mousemove', update)
  })

  // Компонент получает только явно возвращённые значения.
  return { x, y }
}
```

```vue
<script setup>
import { useMouse } from '@/composables/useMouse'

// Источник каждой переменной виден непосредственно в компоненте.
const { x: mouseX, y: mouseY } = useMouse()
</script>

<template>
  <p>Координаты: {{ mouseX }}, {{ mouseY }}</p>
</template>
```

Composable имеет явный импорт, явно возвращает публичные значения и позволяет переименовать их при деструктуризации. Один composable может принимать результат другого через аргументы без скрытой связи по именам.

### Миграция mixin

Практический порядок переноса:

1. Найдите все `data`, `computed`, `methods`, watchers и hooks, относящиеся к одной задаче.
2. Создайте функцию с префиксом `use`, например `usePagination()`.
3. Замените `data` на `ref()` или `reactive()`.
4. Замените `computed` и watchers на одноимённые функции Composition API.
5. Перенесите подписки и их очистку в lifecycle hooks composable.
6. Сделайте скрытые зависимости явными аргументами функции.
7. Верните только те refs и функции, которые нужны вызывающему компоненту.
8. Подключите composable и удалите mixin после проверки всех потребителей.

При возврате нескольких значений обычно используют обычный объект с отдельными refs:

```js
import { ref } from 'vue'

export function usePagination() {
  const page = ref(1)
  const isLoading = ref(false)

  function nextPage() {
    page.value++
  }

  return { page, isLoading, nextPage }
}
```

Такой объект можно деструктурировать без потери реактивности.

### Что использовать

| Задача | Подход |
|---|---|
| Переиспользуемая реактивная логика | Composable |
| Логика вместе с разметкой | Компонент |
| Низкоуровневая работа с DOM-элементом | Пользовательская директива |
| Данные для глубокого дерева компонентов | `provide` / `inject` |
| Установка возможностей на уровне приложения | Plugin |
| Поддержка существующего Options API-кода | Mixin, затем постепенная миграция |

Для нового Vue 3-кода mixin обычно не нужен. Его полезно понимать для сопровождения старых компонентов и сторонних библиотек.

### Полезные ссылки

- [Mixins в API Vue](https://vuejs.org/api/options-composition.html#mixins)
- [Почему composables предпочтительнее mixins](https://vuejs.org/guide/reusability/composables.html#vs-mixins)
- [Глобальный `app.mixin()`](https://vuejs.org/api/application.html#app-mixin)

## Частые ошибки

- Composable возвращает `reactive({ ... })` вместо объекта с отдельными `ref` → после деструктуризации `const { page } = usePagination()` значения перестают обновляться → возвращать обычный объект с `ref`, либо не деструктурировать `reactive`.
- `onMounted` или `watch` вызваны внутри composable асинхронно, после `await` → предупреждение `onMounted is called when there is no active component instance`, хук не срабатывает → вызывать хуки синхронно в начале composable, до первого `await`.
- Подписка на `window` добавлена в `mounted` mixin или `onMounted` composable без очистки → после удаления компонента обработчик продолжает работать, утечка памяти и ошибки на размонтированном компоненте → снимать подписку в `beforeUnmount` или `onBeforeUnmount`.
- Два mixins объявляют одно имя `loading` → одно значение молча перезаписывает другое, состояние загрузки ведёт себя непредсказуемо → переносить логику в composable и переименовывать при деструктуризации.
- Mixin полагается на метод, который должен быть в компоненте → при подключении к другому компоненту `this.save is not a function` → передавать зависимости явно, как аргументы composable.

## Когда не использовать

Mixin для нового кода на Composition API не нужен: composable делает то же самое с явным импортом и явным возвратом значений. Mixins и `extends` остаются для сопровождения старых компонентов на Options API и сторонних библиотек.

Composable тоже не универсален. Если логика неотделима от разметки, лучше сделать компонент со слотами; если нужно общее состояние на всё приложение, а не копия на каждый вызов, — стор [Pinia](pinia.md); для прямой работы с DOM-элементом — пользовательская директива из заметки [Пользовательские возможности Vue](vue_custom.md).

## Связанные темы

- [Composition API и Options API](composition_options_api.md) — два стиля компонентов, под которые сделаны composables и mixins
- [Жизненный цикл Vue](lifecycle.md) — хуки, в которых mixin и composable подписываются и очищают ресурсы
- [Пользовательские возможности Vue](vue_custom.md) — директивы и `provide`/`inject` как альтернативы
- [Pinia](pinia.md) — общее состояние вместо композабла с копией на каждый вызов
