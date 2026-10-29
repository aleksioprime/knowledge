# Прототипы и прототипное наследование

Прототипы связывают объекты в цепочки наследования. Благодаря этому несколько объектов могут использовать одно поведение, а JavaScript не обязан хранить отдельную копию каждого метода в каждом объекте.

## Прототип и прототипное наследование

Каждый обычный объект имеет внутреннюю ссылку `[[Prototype]]`. Её значением может быть другой объект или `null`. Прототип позволяет нескольким объектам использовать общие методы, не копируя их в каждый объект.

При чтении свойства JavaScript:

1. ищет собственное свойство объекта;
2. если его нет, переходит к прототипу;
3. продолжает поиск вверх по цепочке;
4. возвращает `undefined`, если цепочка закончилась на `null`.

```js
const animal = {
  speak() {
    return 'звук'
  },
}

const dog = Object.create(animal)
dog.name = 'Бим'
dog.speak() // 'звук'
```

Это прототипное наследование: объект `dog` наследует поведение непосредственно от объекта `animal`.

Собственное свойство скрывает одноимённое унаследованное свойство, но не удаляет его из прототипа:

```js
const settings = { theme: 'light' }
const userSettings = Object.create(settings)

userSettings.theme = 'dark'

userSettings.theme // 'dark'
delete userSettings.theme
userSettings.theme // 'light'
```

Циклическую цепочку создать нельзя: объект не может стать прототипом самого себя прямо или косвенно.

## Как получить или задать прототип

Предпочтительнее задавать прототип во время создания объекта:

```js
const dog = Object.create(animal)

const cat = {
  __proto__: animal,
  name: 'Мурка',
}
```

Современные методы чтения и изменения прототипа:

```js
Object.getPrototypeOf(dog) === animal // true
Object.setPrototypeOf(dog, otherPrototype)
```

`Object.setPrototypeOf()` изменяет прототип уже существующего объекта. Такая операция может ухудшить производительность, поэтому обычно структуру задают заранее через `Object.create()`, функцию-конструктор или `class`.

## Что такое `__proto__`

`__proto__` — устаревший accessor, унаследованный от `Object.prototype`. Он предоставляет доступ к внутреннему `[[Prototype]]`, но сам не является этим внутренним слотом.

```js
dog.__proto__ === Object.getPrototypeOf(dog) // true
```

В новом коде для чтения и изменения используют `Object.getPrototypeOf()` и `Object.setPrototypeOf()`. Особая запись `__proto__` внутри литерала объекта всё ещё может использоваться для задания прототипа при создании.

Прототипом может быть только объект или `null`. Попытка передать другое значение в `Object.setPrototypeOf()` приводит к `TypeError`. Историческое присваивание через `__proto__` может вести себя менее очевидно — это ещё одна причина не использовать его как основной API.

## Свойство `prototype` функции

Нужно различать два понятия:

- `Object.getPrototypeOf(object)` возвращает прототип конкретного объекта;
- `Constructor.prototype` — обычное свойство функции-конструктора, которое `new` назначит прототипом будущих экземпляров.

```js
function User(name) {
  this.name = name
}

User.prototype.greet = function () {
  return `Привет, ${this.name}`
}

const user = new User('Анна')

Object.getPrototypeOf(user) === User.prototype // true
user.greet()                                   // 'Привет, Анна'
```

У объекта `user` нет собственного метода `greet`: он найден в `User.prototype`. Обычный объект не обязан иметь свойство `.prototype`, а стрелочная функция не может быть конструктором и обычно не имеет такого свойства.

По умолчанию `User.prototype` содержит свойство `constructor`, ссылающееся на `User`. Если полностью заменить объект прототипа, ссылку обычно восстанавливают:

```js
User.prototype = {
  constructor: User,
  greet() {
    return `Привет, ${this.name}`
  },
}
```

Менять `Constructor.prototype` лучше до создания экземпляров: старые объекты сохраняют ссылку на прежний прототип.

## Как `new` использует прототип

Упрощённо выражение `new User('Анна')`:

1. создаёт новый объект;
2. устанавливает его `[[Prototype]]` равным `User.prototype`;
3. вызывает `User` с новым объектом в качестве `this`;
4. обычно возвращает новый объект.

Если свойство `User.prototype` содержит не объект, для прототипа экземпляра используется `Object.prototype`.

## Встроенные прототипы

Встроенные объекты также используют прототипные цепочки:

```js
const numbers = [1, 2, 3]

Object.getPrototypeOf(numbers) === Array.prototype // true
Object.getPrototypeOf(Array.prototype) === Object.prototype // true
Object.getPrototypeOf(Object.prototype) === null // true
```

Метод `numbers.map()` находится в `Array.prototype`, а `numbers.toString()` в итоге доступен через цепочку прототипов. Функции, даты, регулярные выражения, Map и другие встроенные объекты имеют собственные прототипы.

Не следует изменять встроенные прототипы, например добавлять `Array.prototype.myMethod`: это может привести к конфликтам с библиотеками, будущими возможностями языка и перечислением свойств.

## Наследование через функции-конструкторы

До появления `class` наследование часто настраивали вручную:

```js
function Animal(name) {
  this.name = name
}

Animal.prototype.speak = function () {
  return `${this.name} издаёт звук`
}

function Dog(name, breed) {
  Animal.call(this, name)
  this.breed = breed
}

Dog.prototype = Object.create(Animal.prototype)
Dog.prototype.constructor = Dog

Dog.prototype.bark = function () {
  return 'Гав'
}

const dog = new Dog('Бим', 'корги')
dog.speak()
dog.bark()
```

Здесь `Animal.call(this, name)` инициализирует собственные поля, а `Object.create(Animal.prototype)` связывает прототипы. Современный `class Dog extends Animal` делает ту же основную настройку декларативнее.

## Проверка цепочки прототипов

`instanceof` проверяет, находится ли `Constructor.prototype` в цепочке прототипов объекта:

```js
dog instanceof Dog // true
dog instanceof Animal // true
dog instanceof Object // true

Dog.prototype.isPrototypeOf(dog) // true
```

`instanceof` не проверяет набор полей или методов объекта. Он отвечает только на вопрос о цепочке прототипов, поэтому результат может измениться после замены `Constructor.prototype` и отличаться для объектов из другого окна браузера.
