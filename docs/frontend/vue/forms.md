# Формы во Vue

Без фреймворка данные формы приходится собирать вручную: читать значения из DOM при отправке, следить за чекбоксами и `select`, сбрасывать поля после сохранения. Во Vue поля связываются с реактивным состоянием через директиву `v-model`, и состояние в JavaScript считается источником данных: начальные значения задают в `ref()` или `reactive()`, а не через HTML-атрибуты `value`, `checked` и `selected`.

## Минимальный пример

```vue
<script setup>
import { ref } from 'vue'

const title = ref('')

function addTask() {
  console.log('Новая задача:', title.value) // Новая задача: Купить хлеб
  title.value = ''
}
</script>

<template>
  <form @submit.prevent="addTask">
    <input v-model.trim="title" placeholder="Название задачи">
    <button type="submit">Добавить</button>
  </form>
</template>
```

## Как это работает

### Простая форма

```vue
<script setup>
import { reactive, ref } from 'vue'

const form = reactive({
  name: '',
  email: '',
  topic: '',
  subscribe: false,
})

const error = ref('')

function submitForm() {
  error.value = ''

  if (!form.name || !form.email) {
    error.value = 'Заполните имя и email'
    return
  }

  const payload = { ...form }
  console.log(payload)
}
</script>

<template>
  <form @submit.prevent="submitForm">
    <label for="name">Имя</label>
    <input id="name" v-model.trim="form.name" type="text">

    <label for="email">Email</label>
    <input id="email" v-model.trim="form.email" type="email">

    <label for="topic">Тема</label>
    <select id="topic" v-model="form.topic">
      <option disabled value="">Выберите тему</option>
      <option value="support">Поддержка</option>
      <option value="feedback">Обратная связь</option>
    </select>

    <label>
      <input v-model="form.subscribe" type="checkbox">
      Получать новости
    </label>

    <p v-if="error" role="alert">{{ error }}</p>

    <button type="submit">Отправить</button>
  </form>
</template>
```

Обработчик установлен на событие `submit` формы, а не на `click` кнопки. Поэтому форма отправляется и по нажатию Enter. Модификатор `.prevent` вызывает `event.preventDefault()` и предотвращает обычную перезагрузку страницы.

### `v-model` для разных полей

`v-model` выбирает нужное DOM-свойство и событие в зависимости от элемента:

```vue
<!-- Строка -->
<input v-model="form.name" type="text">

<!-- Многострочный текст -->
<textarea v-model="form.message"></textarea>

<!-- Boolean -->
<input v-model="form.agree" type="checkbox">

<!-- Выбранное значение -->
<input v-model="form.delivery" type="radio" value="courier">
<input v-model="form.delivery" type="radio" value="pickup">

<!-- Одно значение -->
<select v-model="form.city">
  <option value="moscow">Москва</option>
  <option value="kazan">Казань</option>
</select>
```

Несколько checkbox можно связать с массивом. В массив попадут значения выбранных полей:

```vue
<script setup>
import { ref } from 'vue'

const skills = ref([])
</script>

<template>
  <label><input v-model="skills" type="checkbox" value="vue"> Vue</label>
  <label><input v-model="skills" type="checkbox" value="pinia"> Pinia</label>
</template>
```

### Модификаторы `v-model`

- `v-model.trim` удаляет пробелы в начале и конце строки;
- `v-model.number` преобразует введённое значение в число, если это возможно;
- `v-model.lazy` обновляет состояние по событию `change`, а не после каждого `input`.

```vue
<input v-model.trim="form.name" type="text">
<input v-model.number="form.age" type="number">
<input v-model.lazy="form.comment" type="text">
```

Если числовое поле очистить, его значением будет пустая строка, а не `0`. Это следует учитывать при валидации и подготовке данных для API.

### Файлы

Для `<input type="file">` директива `v-model` не используется. Файлы нужно получать из события `change`:

```vue
<script setup>
import { ref } from 'vue'

const file = ref(null)

function selectFile(event) {
  file.value = event.target.files?.[0] ?? null
}
</script>

<template>
  <input type="file" @change="selectFile">
</template>
```

Для отправки файла создайте `FormData`. Обычные данные формы можно отправить как JSON. Примеры запросов находятся в разделе [HTTP-запросы во Vue](http_requests.md).

### Практические рекомендации

- Связывайте `label` и поле через `for` и `id` — это улучшает доступность формы.
- Для кнопки отправки явно указывайте `type="submit"`; для остальных кнопок внутри формы — `type="button"`.
- Показывайте ошибки рядом с соответствующими полями или в блоке с `role="alert"`.
- Во время асинхронной отправки блокируйте кнопку через `:disabled="isSubmitting"`, чтобы избежать повторных запросов.
- Проверяйте данные и на клиенте, и на сервере: клиентская валидация улучшает интерфейс, но не защищает backend.

### Полезные ссылки

- [Работа с полями формы в документации Vue](https://vuejs.org/guide/essentials/forms.html)
- [Обработка событий и модификатор `.prevent`](https://vuejs.org/guide/essentials/event-handling.html)

## Частые ошибки

- Обработчик повешен на `@click` кнопки, а не на `@submit` формы → по Enter форма отправляется браузером и страница перезагружается, обработчик не вызывается → перенести обработчик на `<form @submit.prevent>`.
- Забыт модификатор `.prevent` → после отправки страница перезагружается, введённые данные и состояние приложения теряются → добавить `.prevent` или вызвать `event.preventDefault()`.
- Начальное значение задано атрибутом `value="Иван"` или `checked` → Vue перезаписывает поле значением из состояния, атрибут игнорируется → задавать начальные значения в `ref()` или `reactive()`.
- Несколько checkbox привязаны к одному `ref(false)` вместо массива → отметка одного переключает все → хранить выбранные значения в `ref([])` и задавать каждому полю `value`.
- `v-model.number` на очищенном поле → в состоянии пустая строка, а в расчётах `NaN` → перед отправкой проверять значение на пустую строку и приводить к числу явно.
- `v-model` на `<input type="file">` → поле не привязывается, Vue сообщает об ошибке → читать файл из `event.target.files` в обработчике `@change`.

## Когда не использовать

Если форма — обычная HTML-форма, которая отправляет данные на сервер и ведёт на новую страницу, `v-model` и JavaScript-обработчик не нужны: достаточно `<form method="post" action="...">`, браузер соберёт и отправит поля сам. Так же не нужно связывать с состоянием поле, значение которого читают один раз при отправке, например скрытое поле с токеном.

Для больших форм с десятками полей, зависимыми правилами валидации и сообщениями об ошибках ручной `reactive` разрастается: проверки, признаки «поле тронуто» и сброс приходится писать для каждого поля. В таком случае берите библиотеку форм с готовой схемой валидации, а `v-model` оставьте для простых форм из нескольких полей.

## Связанные темы

- [События в Vue](events.md) — обработчики и модификаторы вроде `.prevent`
- [Реактивность в Vue](reactivity.md) — `ref` и `reactive` как источник данных формы
- [HTTP-запросы во Vue](http_requests.md) — отправка данных формы и файлов
- [Debounce и throttle во Vue](debounce_throttle.md) — ограничение частоты проверок при вводе
