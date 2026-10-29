# Формы во Vue

Vue связывает поля формы с реактивным состоянием через директиву `v-model`. Состояние в JavaScript считается источником данных: начальные значения нужно задавать в `ref()` или `reactive()`, а не через HTML-атрибуты `value`, `checked` и `selected`.

## Простая форма

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

## `v-model` для разных полей

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

## Модификаторы `v-model`

- `v-model.trim` удаляет пробелы в начале и конце строки;
- `v-model.number` преобразует введённое значение в число, если это возможно;
- `v-model.lazy` обновляет состояние по событию `change`, а не после каждого `input`.

```vue
<input v-model.trim="form.name" type="text">
<input v-model.number="form.age" type="number">
<input v-model.lazy="form.comment" type="text">
```

Если числовое поле очистить, его значением будет пустая строка, а не `0`. Это следует учитывать при валидации и подготовке данных для API.

## Файлы

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

## Практические рекомендации

- Связывайте `label` и поле через `for` и `id` — это улучшает доступность формы.
- Для кнопки отправки явно указывайте `type="submit"`; для остальных кнопок внутри формы — `type="button"`.
- Показывайте ошибки рядом с соответствующими полями или в блоке с `role="alert"`.
- Во время асинхронной отправки блокируйте кнопку через `:disabled="isSubmitting"`, чтобы избежать повторных запросов.
- Проверяйте данные и на клиенте, и на сервере: клиентская валидация улучшает интерфейс, но не защищает backend.

## Полезные ссылки

- [Работа с полями формы в документации Vue](https://vuejs.org/guide/essentials/forms.html)
- [Обработка событий и модификатор `.prevent`](https://vuejs.org/guide/essentials/event-handling.html)
