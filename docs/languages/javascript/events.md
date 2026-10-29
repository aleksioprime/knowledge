# События в браузере

Событие сообщает программе, что в браузере что-то произошло: пользователь нажал кнопку, отправил форму, ввёл текст или изменился размер окна. Обработчик подписывается на такое событие и выполняет нужную реакцию.

## Что такое событие

Событие — сообщение о том, что в браузере что-то произошло. Источником может быть пользователь, браузер или код приложения:

- пользователь нажал кнопку, ввёл текст или отправил форму;
- документ загрузился;
- изменился размер окна;
- завершилась анимация;
- приложение самостоятельно отправило пользовательское событие.

Объекты, способные отправлять события, реализуют интерфейс `EventTarget`. К ним относятся элементы DOM, `document`, `window`, `AbortSignal` и многие другие Web API.

Обработчик события (event handler, listener) — функция, вызываемая при наступлении события. Подписку на события также называют прослушиванием событий.

```js
const button = document.querySelector('[data-save]')

button.addEventListener('click', (event) => {
  console.log('Кнопка нажата', event)
})
```

## Способы добавить обработчик

### HTML-атрибут

```html
<button onclick="save()">Сохранить</button>
```

Так разметка смешивается с JavaScript, а строковый код сложнее поддерживать и ограничивать политикой CSP. В современном коде этот способ обычно не используют.

### Свойство `on...`

DOM-элемент имеет свойства вроде `onclick`. В такое свойство можно записать одну функцию-обработчик; следующая запись заменит предыдущую.

```js
button.onclick = function (event) {
  console.log(event.type)
}
```

В свойстве может находиться только один обработчик. Новое присваивание заменяет предыдущий, а `null` удаляет его:

```js
button.onclick = null
```

### `addEventListener()`

Этот способ позволяет независимо зарегистрировать несколько обработчиков одного события и передать дополнительные настройки подписки.

```js
function handleClick(event) {
  console.log(event.currentTarget)
}

button.addEventListener('click', handleClick)
```

`addEventListener(type, listener, options)` — основной способ регистрации. Он позволяет добавить несколько независимых обработчиков одного события и настроить их поведение.

```js
button.addEventListener('click', handleClick, {
  capture: false,
  once: true,
  passive: false,
})
```

- `capture` запускает listener на фазе погружения;
- `once` автоматически удаляет его после первого вызова;
- `passive` обещает, что обработчик не вызовет `preventDefault()`;
- `signal` позволяет удалить обработчик через `AbortController`.

## Удаление обработчика

Для `removeEventListener()` нужны тот же тип события, та же функция и то же значение `capture`:

```js
function handleClick(event) {
  console.log(event.type)
}

button.addEventListener('click', handleClick)
button.removeEventListener('click', handleClick)
```

Следующий вариант не удалит listener, потому что две стрелочные функции — разные объекты:

```js
button.addEventListener('click', () => save())
button.removeEventListener('click', () => save()) // не сработает
```

Обработчик можно удалить автоматически после первого вызова:

```js
button.addEventListener('click', save, { once: true })
```

Или объединить жизненный цикл нескольких обработчиков одним сигналом:

```js
const controller = new AbortController()

button.addEventListener('click', save, {
  signal: controller.signal,
})

window.addEventListener('resize', updateLayout, {
  signal: controller.signal,
})

controller.abort() // удалит оба обработчика
```

Для обработчика, назначенного через `onclick`, достаточно присвоить `null`. HTML-атрибут можно удалить через `removeAttribute('onclick')`, хотя inline-обработчики лучше не создавать.

## Объект события

Браузер передаёт listener объект события. Базовые свойства и методы определены интерфейсом `Event`:

| Свойство или метод | Значение |
| --- | --- |
| `type` | тип события, например `'click'` |
| `target` | исходный объект, на котором возникло событие |
| `currentTarget` | объект, listener которого выполняется сейчас |
| `eventPhase` | текущая фаза распространения |
| `bubbles` | поддерживает ли событие всплытие |
| `cancelable` | можно ли отменить стандартное действие |
| `defaultPrevented` | было ли вызвано `preventDefault()` |
| `timeStamp` | время создания события в шкале времени среды |
| `preventDefault()` | отменяет стандартное действие, если это разрешено |
| `stopPropagation()` | останавливает дальнейшее распространение |
| `stopImmediatePropagation()` | дополнительно не даёт вызваться следующим listeners текущего объекта |

```js
document.addEventListener('click', (event) => {
  console.log(event.type)
  console.log(event.target)
  console.log(event.currentTarget)
})
```

Конкретные виды событий расширяют `Event`:

- `MouseEvent` содержит `clientX`, `clientY`, `button`;
- `PointerEvent` — `pointerId`, `pointerType`, `pressure`;
- `KeyboardEvent` — `key`, `code`, `ctrlKey`, `shiftKey`;
- `InputEvent` — `data`, `inputType`;
- `CustomEvent` — пользовательское поле `detail`.

`target` остаётся исходной целью при прохождении события по дереву, а `currentTarget` меняется и указывает на элемент, чей обработчик выполняется сейчас. После завершения listener значение `currentTarget` обычно становится `null`, поэтому нужную ссылку сохраняют заранее.

## Фазы распространения события

Для события в DOM-дереве путь обычно состоит из трёх фаз:

1. capture — событие идёт от `window` и предков к целевому элементу;
2. target — достигает цели;
3. bubble — поднимается от цели обратно к предкам.

```text
window → document → body → list → button
                                  target
window ← document ← body ← list ← button
```

Обычный listener вызывается на фазе target или bubble. Для capture передают `{ capture: true }`:

```js
document.addEventListener('click', handleCapture, {
  capture: true,
})

document.addEventListener('click', handleBubble)
```

Значения `event.eventPhase`:

- `Event.CAPTURING_PHASE` (`1`);
- `Event.AT_TARGET` (`2`);
- `Event.BUBBLING_PHASE` (`3`).

Не каждое событие всплывает. Например, `focus` и `blur` не всплывают; для делегирования часто используют всплывающие `focusin` и `focusout`.

## Остановка распространения

`stopPropagation()` не даёт событию продолжить путь к следующим объектам дерева:

```js
button.addEventListener('click', (event) => {
  event.stopPropagation()
})
```

Он не отменяет стандартное действие и не останавливает другие listeners того же элемента. Для остановки следующих listeners на текущем объекте используют `stopImmediatePropagation()`:

```js
button.addEventListener('click', (event) => {
  event.stopImmediatePropagation()
})
```

Останавливать распространение без необходимости не стоит: это может сломать делегирование, аналитику и другие независимые обработчики страницы.

## Отмена стандартного действия

Некоторые события запускают действие браузера по умолчанию:

- клик по ссылке открывает адрес;
- отправка формы перезагружает страницу или переходит по `action`;
- нажатие клавиши может ввести символ;
- контекстное меню открывается по `contextmenu`.

`preventDefault()` отменяет такое действие, если `event.cancelable === true`:

```js
const form = document.querySelector('form')

form.addEventListener('submit', (event) => {
  event.preventDefault()
  saveForm(new FormData(form))
})
```

```js
link.addEventListener('click', (event) => {
  event.preventDefault()
  router.navigate(link.href)
})
```

Проверить отмену можно через `event.defaultPrevented`. В passive-listener вызов `preventDefault()` игнорируется, потому что listener заранее пообещал не блокировать стандартное действие.

`return false` не является общей заменой `preventDefault()` в обработчике `addEventListener`. Такое поведение встречается у inline-обработчиков и некоторых библиотек, но в современном DOM-коде действие отменяют явно.

## Делегирование событий

Делегирование — регистрация одного listener на общем предке вместо отдельных listeners на каждом дочернем элементе. Оно основано на всплытии.

```html
<ul class="user-list">
  <li><button data-user-id="1">Анна</button></li>
  <li><button data-user-id="2">Иван</button></li>
</ul>
```

```js
const list = document.querySelector('.user-list')

list.addEventListener('click', (event) => {
  if (!(event.target instanceof Element)) return

  const button = event.target.closest('[data-user-id]')

  if (!button || !list.contains(button)) return

  openUser(button.dataset.userId)
})
```

`closest()` нужен потому, что пользователь может нажать на вложенную иконку внутри кнопки. Проверка `list.contains(button)` не позволяет случайно обработать подходящий элемент за границей контейнера.

Преимущества делегирования:

- меньше обработчиков;
- динамически добавленные потомки работают без новой подписки;
- логика однотипных элементов хранится в одном месте.

Ограничения:

- событие должно всплывать либо обрабатываться на capture-фазе;
- нужно определить подходящую цель через `target`, `closest()` и `matches()`;
- один большой обработчик не должен превращаться в сложный набор несвязанных условий.

## Пользовательские события

Обычное событие создают через `Event`, а событие с данными — через `CustomEvent`:

```js
const event = new CustomEvent('cart:add', {
  detail: {
    productId: 42,
    quantity: 2,
  },
  bubbles: true,
  cancelable: true,
})
```

Подписка ничем не отличается от встроенного события:

```js
document.addEventListener('cart:add', (event) => {
  console.log(event.detail.productId)
})
```

Событие инициируется методом `dispatchEvent()`:

```js
const wasNotCanceled = element.dispatchEvent(event)
```

`dispatchEvent()` вызывает обработчики синхронно. Он возвращает `false`, если событие было отменено через `preventDefault()`, и `true` в остальных случаях.

Для пользовательского типа выбирайте понятное уникальное имя. Двоеточие вроде `cart:add` не обязательно, но помогает обозначить пространство имён.

## Очистка обработчиков

Обработчик сохраняет ссылки на функцию и доступные ей значения. В долгоживущих приложениях ненужные listeners нужно удалять через `removeEventListener`, `{ once: true }` или `AbortSignal`.

Особенно это важно, когда уничтожается компонент, закрывается модальное окно или прекращается работа временного интерфейса. Делегирование также сокращает количество подписок, которые приходится отслеживать.
