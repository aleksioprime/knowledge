# Объекты, прототипы и классы

## Объекты

```js
const user = {
  id: 42,
  name: 'Alex',
  ['is' + 'Active']: true,
  greet() {
    return `Привет, ${this.name}`
  },
}

user.name
user['isActive']
```

Проверять собственное свойство следует через `Object.hasOwn(user, 'name')`. Оператор `in` учитывает и свойства в цепочке прототипов.

## Деструктуризация

```js
const { id, name, role = 'user' } = user

function printUser({ name, role = 'user' }) {
  console.log(`${name}: ${role}`)
}
```

`Object.keys`, `Object.values` и `Object.entries` возвращают собственные перечисляемые свойства со строковыми ключами.

## Прототипы

Объект может наследовать свойства от другого объекта через внутреннюю ссылку `[[Prototype]]`. При чтении отсутствующего свойства движок идёт вверх по цепочке прототипов.

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

## Классы

Синтаксис `class` является удобной оболочкой над прототипным наследованием:

```js
class User {
  #token

  constructor(name, token) {
    this.name = name
    this.#token = token
  }

  greet() {
    return `Привет, ${this.name}`
  }

  static fromJSON(data) {
    return new User(data.name, data.token)
  }
}
```

Поля с `#` приватны на уровне языка. Методы экземпляра размещаются в прототипе, а `static`-методы принадлежат самому классу.

Композиция часто проще глубоких иерархий наследования: объект получает необходимые функции и зависимости явно, а не через длинную цепочку классов.
