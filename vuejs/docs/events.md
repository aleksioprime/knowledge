# События в Vue

## Что такое события в Vue

В Vue чаще всего работают с двумя категориями событий:

- DOM-события элементов: `click`, `input`, `change`, `submit`, `keydown`
- пользовательские события компонентов: события, которые компонент отправляет через `emit`

Этот материал в первую очередь про DOM-события в шаблоне. Про `emit` и связь child -> parent см. [components_basics.md](components_basics.md).

## Подписка на событие

Для подписки на событие используют `v-on` или короткую форму `@`.

```vue
<template>
  <button v-on:click="handleClick">Нажми</button>
  <button @click="handleClick">Нажми</button>
</template>

<script setup>
function handleClick() {
  console.log('Клик')
}
</script>
```

- `v-on:click` и `@click` равнозначны
- на практике почти всегда используют короткую форму `@`
- тот же подход работает для `input`, `change`, `focus`, `blur`, `submit`, `keydown`

## Обработчик как ссылка или выражение

В шаблоне можно передать либо функцию, либо простое выражение.

```vue
<template>
  <button @click="increment">+</button>
  <button @click="count++">+</button>
</template>
```

- `@click="increment"` передает ссылку на функцию
- `@click="count++"` выполняет простое выражение прямо в шаблоне
- если в обработчике есть логика, ветвления или несколько шагов, лучше вынести это в функцию

```vue
<script setup>
function handleClick() {
  console.log('Кнопка нажата')
}
</script>

<template>
  <button @click="handleClick">Нажми</button>
  <button @click="handleClick()">Нажми</button>
</template>
```

- `@click="handleClick"` обычно достаточно
- `@click="handleClick()"` тоже корректно, но чаще используют, когда нужно явно передать свои аргументы

## Объект события и `$event`

`$event` - это объект текущего события.

```vue
<template>
  <input @input="onInput($event)" />
</template>

<script setup>
function onInput(event) {
  console.log(event.target.value)
}
</script>
```

Если обработчик передан без аргументов, Vue сам передаст объект события первым параметром.

```vue
<template>
  <form @submit.prevent="onSubmit">
    <button type="submit">Сохранить</button>
  </form>
</template>

<script setup>
function onSubmit(event) {
  console.log(event)
}
</script>
```

### Когда нужен `$event`

`$event` нужен, когда вы хотите:

- получить доступ к `event.target`, `event.currentTarget`, `event.key`
- передать в обработчик и свои аргументы, и сам объект события
- использовать короткое выражение прямо в шаблоне

```vue
<template>
  <button @click="selectUser(user.id, $event)">Выбрать</button>
</template>

<script setup>
function selectUser(userId, event) {
  console.log(userId)
  console.log(event.type)
}
</script>
```

## Частые DOM-события

### `click`

Используется для кнопок, ссылок, карточек, иконок.

```vue
<button @click="openModal">Открыть</button>
```

### `input`

Срабатывает при каждом изменении значения поля.

```vue
<template>
  <input :value="name" @input="name = $event.target.value" />
</template>
```

Подходит, когда нужна реакция на каждый ввод символа.

### `change`

Срабатывает, когда изменение подтверждено.

```vue
<select @change="status = $event.target.value">
  <option value="active">active</option>
  <option value="archived">archived</option>
</select>
```

Для текстового поля `change` обычно срабатывает после потери фокуса, а не на каждый символ.

### `submit`

Используется для формы.

```vue
<form @submit.prevent="onSubmit">
  <button type="submit">Сохранить</button>
</form>
```

Почти всегда для форм нужен `.prevent`, чтобы браузер не перезагружал страницу.

### `keydown` и `keyup`

Используются для горячих клавиш и отправки по Enter.

```vue
<input @keydown.enter="submit" />
<input @keydown.esc="close" />
```

## `preventDefault` и `stopPropagation`

В браузере объект события дает доступ к методам:

- `event.preventDefault()` - отменить стандартное поведение браузера
- `event.stopPropagation()` - остановить всплытие события выше по DOM

Во Vue это можно делать вручную или через модификаторы.

### Вариант через объект события

```vue
<script setup>
function onLinkClick(event) {
  event.preventDefault()
  console.log('Переход перехвачен')
}
</script>

<template>
  <a href="/profile" @click="onLinkClick">Профиль</a>
</template>
```

```vue
<script setup>
function onInnerClick(event) {
  event.stopPropagation()
  console.log('Клик только по внутреннему элементу')
}
</script>

<template>
  <div @click="onCardClick">
    <button @click="onInnerClick">Действие</button>
  </div>
</template>
```

### Предпочтительный вариант через модификаторы

```vue
<template>
  <a href="/profile" @click.prevent="openProfile">Профиль</a>
  <button @click.stop="toggleMenu">Меню</button>
</template>
```

- `.prevent` заменяет `event.preventDefault()`
- `.stop` заменяет `event.stopPropagation()`
- для типичных сценариев модификаторы обычно читаются лучше, чем ручной вызов методов

## Модификаторы событий

### `.prevent`

Отменяет стандартное поведение.

```vue
<form @submit.prevent="saveForm">
```

### `.stop`

Останавливает всплытие события.

```vue
<button @click.stop="removeItem">Удалить</button>
```

### `.self`

Вызывает обработчик только если событие произошло на самом элементе, а не на его дочернем узле.

```vue
<div class="modal-backdrop" @click.self="closeModal">
  <div class="modal">...</div>
</div>
```

Полезно для закрытия модалки по клику на фон, но не по клику внутри содержимого.

### `.once`

Обработчик выполнится только один раз.

```vue
<button @click.once="sendAnalytics">Первый клик</button>
```

### `.capture`

Переводит обработку на фазу capture.

```vue
<div @click.capture="trackClick">
```

Используется редко, обычно только в специфических сценариях всплытия.

### Порядок модификаторов

Модификаторы комбинируются.

```vue
<form @submit.prevent.stop="submitForm">
```

Обычно достаточно простых сочетаний вроде:

- `@submit.prevent`
- `@click.stop`
- `@click.prevent`

## Модификаторы клавиш и мыши

Vue позволяет уточнять события клавиатуры и мыши прямо в шаблоне.

```vue
<input @keydown.enter="submit" />
<input @keydown.tab="focusNext" />
<div @click.ctrl="multiSelect" />
```

Часто встречаются:

- `.enter`
- `.tab`
- `.esc`
- `.space`
- `.ctrl`
- `.shift`
- `.alt`
- `.exact`

Пример:

```vue
<button @click.ctrl.exact="openInNewMode">Открыть</button>
```

Это означает: сработать только при клике с зажатым Ctrl без дополнительных модификаторов.

## Частые паттерны

### Инпут без `v-model`

Когда важно явно показать механику обновления значения:

```vue
<template>
  <input :value="email" @input="email = $event.target.value" />
</template>
```

Это полезно для понимания того, что `v-model` внутри опирается на значение и событие обновления.

### Отправка формы

```vue
<template>
  <form @submit.prevent="onSubmit">
    <input v-model="name" />
    <button type="submit">Сохранить</button>
  </form>
</template>
```

- бизнес-логику лучше держать в `onSubmit`
- `.prevent` почти всегда нужен для SPA-форм

### Клик по карточке и отдельная кнопка внутри

```vue
<template>
  <article class="card" @click="openDetails(item.id)">
    <button @click.stop="toggleFavorite(item.id)">☆</button>
  </article>
</template>
```

Без `.stop` клик по кнопке может одновременно вызвать и обработчик карточки.

### Передача своих аргументов вместе с событием

```vue
<template>
  <button @click="removeItem(item.id, $event)">Удалить</button>
</template>
```

Этот паттерн полезен, когда одновременно нужен контекст элемента и доступ к самому событию.

### Закрытие по клику вне контента

```vue
<template>
  <div class="overlay" @click.self="close">
    <div class="dialog">...</div>
  </div>
</template>
```

Это один из самых частых сценариев для `.self`.

## Что выбрать: модификатор или явный вызов метода

Обычно правило простое:

- если нужно стандартное поведение уровня шаблона, используйте модификатор
- если логика зависит от условий или нескольких веток, используйте объект события в функции

```vue
<script setup>
function onSubmit(event) {
  if (isReadonly.value) {
    event.preventDefault()
    return
  }

  save()
}
</script>
```

Здесь `.prevent` уже не подходит, потому что отмена действия зависит от условия.

## Частые ошибки

- Использовать `change` там, где нужен отклик на каждый ввод, и наоборот
- Забывать `.prevent` на `submit` в SPA-форме
- Передавать слишком много логики прямо в шаблон
- Не использовать `.stop`, когда внутри кликабельного контейнера есть отдельные кнопки
- Путать DOM-события и пользовательские события компонентов
- Ожидать, что `@click` на компоненте работает так же, как на обычном DOM-элементе, без понимания API самого компонента

## Краткое правило

- DOM-события нужны для работы с элементами шаблона
- `emit` нужен для общения компонента с родителем
- `$event` нужен, когда требуется доступ к объекту события
- `.prevent`, `.stop`, `.self`, `.once` покрывают большую часть повседневных сценариев
