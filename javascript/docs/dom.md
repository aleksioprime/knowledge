# DOM

DOM представляет HTML-документ как дерево объектов, с которыми может работать JavaScript. Через него программа находит элементы, читает и меняет содержимое, создаёт новые узлы и перестраивает страницу.

## Что такое DOM

DOM (Document Object Model) — объектная модель документа. Браузер разбирает HTML и представляет документ в виде дерева объектов, с которыми JavaScript может работать через API.

```html
<main>
  <h1>Публикации</h1>
  <p>Новых публикаций нет</p>
</main>
```

Упрощённое DOM-дерево:

```text
Document
└── html
    ├── head
    └── body
        └── main
            ├── h1
            │   └── Text «Публикации»
            └── p
                └── Text «Новых публикаций нет»
```

DOM не является самим HTML-текстом. HTML служит исходными данными, а DOM — текущей объектной моделью страницы. JavaScript может изменить дерево после загрузки, не переписывая исходный HTML-файл на сервере.

DOM предоставляет браузер, а не язык ECMAScript. Например, `document` существует в браузере, но обычно отсутствует в чистой среде Node.js.

## Структура DOM

Все части дерева являются узлами (`Node`). Основные типы:

- `Document` — корень документа, доступный через `document`;
- `DocumentType` — декларация `<!doctype html>`;
- `Element` — HTML-элемент, например `<div>`;
- `Text` — текст внутри элемента;
- `Comment` — HTML-комментарий;
- `DocumentFragment` — временный контейнер для группы узлов.

`Element` является разновидностью `Node`, но не каждый `Node` является элементом. Например, текст и комментарий — узлы, но не элементы.

Полезные точки входа:

```js
document.documentElement // читаем свойство documentElement; результат: <html>
document.head // читаем свойство head; результат: <head>
document.body // читаем свойство body; результат: <body>
```

## Навигация по DOM

DOM можно обходить по родителям, дочерним узлам и соседям.

### Навигация по всем узлам

| Свойство | Что возвращает |
| --- | --- |
| `parentNode` | родительский узел или `null` |
| `childNodes` | все непосредственные дочерние узлы |
| `firstChild`, `lastChild` | первый или последний дочерний узел |
| `previousSibling`, `nextSibling` | предыдущий или следующий соседний узел |

### Навигация только по элементам

| Свойство | Что возвращает |
| --- | --- |
| `parentElement` | родительский элемент или `null` |
| `children` | непосредственные дочерние элементы |
| `firstElementChild`, `lastElementChild` | первый или последний дочерний элемент |
| `previousElementSibling`, `nextElementSibling` | соседний элемент |

```js
const list = document.querySelector('.user-list') // находим первый элемент по CSS-селектору

list.parentElement // читаем свойство parentElement
list.children // читаем свойство children
list.firstElementChild // читаем свойство firstElementChild
list.nextElementSibling // читаем свойство nextElementSibling
```

На практике свойства с `Element` в названии часто удобнее, потому что они пропускают текстовые узлы с пробелами и переносами строк.

## Что содержит `childNodes`

`childNodes` возвращает живой `NodeList` всех непосредственных дочерних узлов: элементов, текста и комментариев.

```html
<ul id="users">
  <li>Анна</li>
  <li>Иван</li>
</ul>
```

```js
const users = document.querySelector('#users') // находим первый элемент по CSS-селектору

users.childNodes // содержит также текстовые узлы с переносами и пробелами
users.children   // содержит только два элемента <li>
```

Пробелы и переносы между тегами могут стать объектами `Text`. Поэтому `firstChild` иногда возвращает текстовый узел, тогда как `firstElementChild` — первый HTML-элемент.

## Живые и статические коллекции

Живая коллекция автоматически отражает последующие изменения DOM:

```js
const liveItems = document.getElementsByClassName('item') // получаем живую коллекцию элементов с указанным классом
console.log(liveItems.length) // выводим значение в консоль; результат: 2

document.body.append(document.createElement('div')) // добавляем узлы или текст в конец элемента
document.body.lastElementChild.className = 'item' // записываем 'item' в свойство className

console.log(liveItems.length) // выводим значение в консоль; результат: 3
```

Основные различия:

| Источник | Тип | Обновляется автоматически |
| --- | --- | ---: |
| `element.children` | `HTMLCollection` | да |
| `element.childNodes` | `NodeList` | да |
| `getElementsByTagName()` | `HTMLCollection` | да |
| `getElementsByClassName()` | `HTMLCollection` | да |
| `querySelectorAll()` | `NodeList` | нет |

Статический результат `querySelectorAll()` фиксируется в момент вызова. Для обычной обработки часто удобнее именно он: коллекция не меняется неожиданно во время перебора.

`HTMLCollection` и `NodeList` — массивоподобные коллекции, но не массивы. У них есть `length` и доступ по индексу, однако нет всех методов `Array`. При необходимости используйте `Array.from(collection)` или `[...collection]`.

## Поиск элементов

| Метод | Результат |
| --- | --- |
| `document.getElementById(id)` | один элемент или `null` |
| `getElementsByClassName(name)` | живая `HTMLCollection` |
| `getElementsByTagName(name)` | живая `HTMLCollection` |
| `document.getElementsByName(name)` | `NodeList` элементов с заданным `name` |
| `querySelector(selector)` | первый подходящий элемент или `null` |
| `querySelectorAll(selector)` | статический `NodeList` всех совпадений |

```js
const form = document.getElementById('profile-form') // находим элемент по уникальному id
const activeButtons = document.querySelectorAll('.button.is-active') // находим все элементы по CSS-селектору
const emailInput = form.querySelector('[name="email"]') // находим первый элемент по CSS-селектору
```

`querySelector()` и `querySelectorAll()` можно вызывать не только у `document`, но и у элемента. Тогда поиск ограничивается его потомками.

Дополнительные методы:

```js
element.matches('.button.is-active') // соответствует ли сам элемент селектору
element.closest('[data-user-id]')    // ближайший подходящий предок, включая сам элемент
```

Некорректный CSS-селектор в `querySelector` или `querySelectorAll` приводит к `DOMException` с именем `SyntaxError`.

### `querySelector` и `querySelectorAll`

Оба метода принимают любой CSS-селектор, но возвращают разное количество результатов:

- `querySelector(selector)` возвращает только первый найденный `Element` или `null`;
- `querySelectorAll(selector)` возвращает статический `NodeList`, который может быть пустым;
- оба принимают любой поддерживаемый CSS-селектор.

```js
document.querySelector('.item')    // первый .item
document.querySelectorAll('.item') // все .item на момент вызова
```

### `getElements...` и `querySelectorAll`

Старые методы `getElements...` отличаются не только синтаксисом поиска, но и видом возвращаемой коллекции:

- методы `getElementsByClassName()` и `getElementsByTagName()` принимают имя, а не произвольный CSS-селектор;
- они возвращают живую `HTMLCollection`;
- `querySelectorAll()` поддерживает сложные CSS-селекторы и возвращает статический `NodeList`;
- `getElementById()` возвращает один элемент и вызывается только у `document`.

Для большинства прикладных запросов удобны `querySelector` и `querySelectorAll`. Специальные `getElement...` тоже допустимы, когда точно соответствуют задаче.

## Изменение текста и HTML

Содержимое элемента можно менять как обычный текст либо как HTML-разметку. Выбор свойства влияет на безопасность и на то, будет ли браузер разбирать теги.

```js
const status = document.querySelector('[data-status]') // находим первый элемент по CSS-селектору

status.textContent = 'Сохранено' // записываем 'Сохранено' в свойство textContent
```

Основные свойства:

| Свойство | Особенность |
| --- | --- |
| `textContent` | читает или заменяет текст без интерпретации HTML |
| `innerText` | учитывает отображение и CSS, поэтому может требовать вычисления layout |
| `innerHTML` | читает или заменяет HTML-разметку внутри элемента |

```js
status.textContent = '<strong>Готово</strong>' // выводит символы как текст
status.innerHTML = '<strong>Готово</strong>'   // создаёт элемент <strong>
```

Для обычного текста используйте `textContent`. Не передавайте непроверенные пользовательские данные в `innerHTML`: это может привести к XSS.

### `innerHTML` и `innerText`

`innerHTML` работает с HTML-разметкой. При записи браузер разбирает строку, удаляет прежних потомков элемента и создаёт новые DOM-узлы:

```js
element.innerHTML = '<button>Сохранить</button>' // записываем '<button>Сохранить</button>' в свойство innerHTML
```

`innerText` работает с текстом так, как он отображается пользователю. При чтении он учитывает CSS и обычно не включает текст скрытых элементов:

```html
<p id="message">
  Видимый текст
  <span hidden>Скрытый текст</span>
</p>
```

```js
const message = document.querySelector('#message') // находим первый элемент по CSS-селектору

message.innerText   // 'Видимый текст'
message.textContent // содержит также 'Скрытый текст'
```

Основные различия:

- `innerHTML` возвращает или принимает строку с разметкой;
- `innerText` возвращает видимый текст без HTML-тегов;
- чтение `innerText` может заставить браузер вычислить стили и layout;
- запись в `innerHTML` пересоздаёт вложенные узлы и может удалить связанные с ними состояния и обработчики;
- непроверенные данные нельзя вставлять через `innerHTML` из-за риска XSS.

Если нужна просто безопасная запись текста, обычно выбирают `textContent`.

## Создание элементов

Новый элемент создаётся методом `document.createElement()`:

```js
const item = document.createElement('li') // создаём новый DOM-элемент, пока не вставляя его в документ
item.classList.add('user-item') // добавляем CSS-класс
item.dataset.userId = '42' // записываем '42' в свойство userId
item.textContent = 'Анна' // записываем 'Анна' в свойство textContent
```

Отдельный текстовый узел можно создать через `document.createTextNode()`:

```js
const text = document.createTextNode('Анна') // создаём отдельный текстовый DOM-узел
```

Созданный узел ещё не находится на странице. Его нужно вставить в DOM.

## Работа с CSS-классами

Свойство `className` читает или заменяет всю строку атрибута `class`:

```js
const button = document.querySelector('.button') // находим первый элемент по CSS-селектору

button.className = 'button button--primary' // записываем 'button button--primary' в свойство className
console.log(button.className) // выводим значение в консоль; результат: 'button button--primary'
```

Присваивание `className` перезаписывает прежний набор классов. Для изменения отдельных классов удобнее `classList` — объект `DOMTokenList`:

```js
button.classList.add('is-active', 'is-visible') // добавляем CSS-класс
button.classList.remove('is-loading') // удаляем DOM-узел
button.classList.contains('is-active') // вызываем button.classList.contains(); результат: true
button.classList.toggle('is-open') // переключаем CSS-класс
button.classList.replace('button--primary', 'button--danger') // заменяем найденный фрагмент
```

В `classList` имя передаётся без точки. Точка нужна только внутри CSS-селектора:

```js
button.classList.add('is-active')       // имя класса
button.matches('.button.is-active')     // CSS-селектор
```

У `toggle()` есть необязательный второй аргумент, который явно задаёт итоговое состояние:

```js
button.classList.toggle('is-disabled', shouldDisable) // переключаем CSS-класс
```

Если `shouldDisable` истинно, класс будет добавлен, иначе — удалён. Это удобнее ручного `if`.

## Вставка элементов

После создания узел существует только в памяти. Чтобы он появился на странице, его нужно вставить в выбранное место DOM-дерева.

```js
const list = document.querySelector('.user-list') // находим первый элемент по CSS-селектору

list.append(item)  // в конец
list.prepend(item) // в начало
item.before(note)  // перед item
item.after(note)   // после item
```

Методы `append`, `prepend`, `before` и `after` принимают несколько узлов и строк. Строки автоматически превращаются в текстовые узлы.

Если вставляемый узел уже находится в DOM, он перемещается, а не копируется.

### `append()` и `appendChild()`

| Особенность | `append()` | `appendChild()` |
| --- | --- | --- |
| Количество аргументов | несколько | один |
| Принимает строки | да | нет, только `Node` |
| Возвращает | `undefined` | вставленный узел |

```js
list.append('Пользователи: ', firstItem, secondItem) // добавляем узлы или текст в конец элемента

const appendedItem = list.appendChild(item) // добавляем один дочерний DOM-узел
appendedItem === item // сравниваем ссылки и убеждаемся, что appendChild() вернул вставленный узел; результат: true
```

### Вставка перед другим элементом

Современный способ:

```js
referenceElement.before(newElement) // вызываем referenceElement.before()
```

Классический способ через родителя:

```js
parentElement.insertBefore(newElement, referenceElement) // вызываем parentElement.insertBefore()
```

`insertBefore()` принимает вставляемый узел и существующий дочерний узел, перед которым нужна вставка. Если вторым аргументом передать `null`, узел добавится в конец.

## Клонирование узлов

Метод `cloneNode(deep)` создаёт копию узла:

```js
const shallowCopy = item.cloneNode(false) // клонируем только сам узел без потомков
const deepCopy = item.cloneNode(true) // глубоко клонируем узел вместе с потомками
```

- `false` или пропущенный аргумент копирует только сам узел;
- `true` также рекурсивно копирует всех потомков;
- атрибуты элемента копируются в обоих случаях;
- копия не вставляется в DOM автоматически.

```js
const copy = item.cloneNode(true) // глубоко клонируем узел вместе с потомками
list.append(copy) // добавляем узлы или текст в конец элемента
```

Обработчики, добавленные через `addEventListener()`, не копируются. Обработчики из HTML-атрибутов вроде `onclick` копируются как атрибуты, но такой способ регистрации лучше не использовать.

Следите за уникальностью `id`: клонирование элемента с `id` может создать в документе несколько элементов с одинаковым идентификатором.

Для клонирования узла из другого документа существует `document.importNode(node, deep)`. Обычному коду одной страницы чаще достаточно `cloneNode()`.

## Удаление элементов

Современный способ удаляет сам узел:

```js
item.remove() // удаляем DOM-узел
```

Через родителя:

```js
const removedItem = list.removeChild(item) // удаляем дочерний узел и сохраняем ссылку на него
```

`removeChild()` требует, чтобы переданный узел был непосредственным ребёнком, и возвращает удалённый узел. Удалённый объект продолжает существовать, пока на него остаются ссылки, и его можно вставить снова.

Для удаления всего содержимого элемента удобно присвоить пустую строку `textContent` или вызвать `replaceChildren()`:

```js
list.replaceChildren() // вызываем list.replaceChildren()
```

## Небольшой итоговый пример

Следующий пример связывает поиск контейнера, создание элементов и безопасную запись текста в одну небольшую функцию отображения списка.

```js
function addUser(user) { // объявляем функцию addUser()
  const list = document.querySelector('.user-list') // находим первый элемент по CSS-селектору
  const item = document.createElement('li') // создаём новый DOM-элемент, пока не вставляя его в документ

  item.className = 'user-item' // записываем 'user-item' в свойство className
  item.dataset.userId = String(user.id) // записываем String(user.id) в свойство userId
  item.textContent = user.name // записываем user.name в свойство textContent

  list.append(item) // добавляем узлы или текст в конец элемента
}
```

Функция находит список, создаёт элемент, безопасно задаёт текст и вставляет узел в конец DOM-дерева.
