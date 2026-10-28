# Teleport во Vue

`<Teleport>` — встроенный компонент Vue, который переносит часть шаблона в другой DOM-элемент. При этом компонент остаётся на прежнем месте в логическом дереве Vue: `props`, события, `provide` / `inject` и отображение в Vue DevTools продолжают работать как обычно.

Teleport чаще всего используют для:

- модальных окон;
- всплывающих уведомлений;
- dropdown-меню и tooltip;
- других overlay-элементов, которым мешают `overflow`, `transform` или контекст `z-index` родителя.

`Teleport` встроен во Vue, поэтому импортировать или регистрировать его не нужно.

## Модальное окно

```vue
<script setup>
import { ref } from 'vue'

const isOpen = ref(false)

function close() {
  isOpen.value = false
}
</script>

<template>
  <button type="button" @click="isOpen = true">
    Открыть окно
  </button>

  <!-- Модальное окно станет дочерним элементом body в реальном DOM. -->
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="modal-backdrop"
      @click.self="close"
    >
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <h2 id="modal-title">Настройки</h2>
        <p>Содержимое модального окна</p>
        <button type="button" @click="close">Закрыть</button>
      </section>
    </div>
  </Teleport>
</template>
```

Без Teleport модальное окно было бы вложено в DOM родительского компонента. Свойства `overflow: hidden`, `transform`, `filter` и локальный stacking context родителя могут мешать полноэкранному позиционированию и `z-index`. Перенос в `body` помогает избежать этих ограничений.

Рабочий пример находится в [`LoginModal.vue`](../examples/posts/src/components/LoginModal.vue).

Teleport отвечает только за расположение DOM. Для доступного модального окна дополнительно нужны управление фокусом, возврат фокуса на открывающую кнопку, закрытие по Escape и при необходимости блокировка прокрутки страницы.

## Свойство `to`

`to` задаёт цель переноса. Обычно это CSS-селектор:

```vue
<Teleport to="body">
  <AppModal />
</Teleport>

<Teleport to="#notifications">
  <AppNotifications />
</Teleport>
```

Для отдельного контейнера добавьте элемент за пределами приложения в `index.html`:

```html
<body>
  <div id="app"></div>
  <div id="modals"></div>
  <script type="module" src="/src/main.js"></script>
</body>
```

```vue
<Teleport to="#modals">
  <AppModal />
</Teleport>
```

Целевой элемент должен существовать в DOM к моменту монтирования Teleport. Предпочтительно располагать его вне корневого элемента Vue-приложения.

## Условное отключение

Prop `disabled` оставляет содержимое на исходном месте вместо переноса. Например, окно можно показывать как overlay на широком экране и как обычный блок на мобильном:

```vue
<!-- При isMobile === true содержимое останется внутри текущего компонента. -->
<Teleport to="body" :disabled="isMobile">
  <AppPanel />
</Teleport>
```

При изменении `disabled` Vue перемещает уже существующие DOM-узлы между исходным местом и целевым контейнером.

## Несколько Teleport с одной целью

Несколько компонентов могут использовать один контейнер:

```vue
<Teleport to="#modals">
  <div>Первое окно</div>
</Teleport>

<Teleport to="#modals">
  <div>Второе окно</div>
</Teleport>
```

Содержимое добавляется в цель по порядку монтирования: более поздний Teleport окажется после предыдущего. Внешний вид и порядок перекрытия по-прежнему определяются CSS и `z-index`.

## Отложенный поиск цели в Vue 3.5+

Начиная с Vue 3.5 prop `defer` откладывает поиск целевого элемента до завершения текущего цикла монтирования. Это позволяет объявить цель позже в том же шаблоне:

```vue
<template>
  <!-- Vue найдёт #late-target в конце текущего цикла монтирования. -->
  <Teleport defer to="#late-target">
    <p>Перенесённое содержимое</p>
  </Teleport>

  <div id="late-target"></div>
</template>
```

`defer` не ожидает цель неопределённое время. Если она появится только в следующем цикле, например после асинхронного запроса, Teleport всё равно сообщит об ошибке.

## Важные особенности

- `Teleport` меняет физическое расположение DOM, но не родительские связи компонентов Vue.
- Scoped-стили компонента продолжают применяться к перенесённым элементам.
- События компонента и `provide` / `inject` работают по логическому дереву Vue.
- CSS-селекторы, зависящие от DOM-вложенности родителя, после переноса могут перестать совпадать.
- При SSR нужна отдельная обработка teleports на стороне серверного рендеринга.

## Полезная ссылка

- [Teleport в официальной документации Vue](https://vuejs.org/guide/built-ins/teleport.html)
