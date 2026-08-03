# Модули

ES modules позволяют явно экспортировать и импортировать значения.

```js
// math.js
export const PI = 3.14159

export function square(value) {
  return value ** 2
}
```

```js
// main.js
import { PI, square as getSquare } from './math.js'

console.log(PI, getSquare(4))
```

## Default export

```js
// User.js
export default class User {}

// main.js
import User from './User.js'
```

У default-импорта имя выбирает потребитель. Named exports сохраняют единые имена, упрощают поиск и обычно предпочтительны для модулей с несколькими экспортами.

## Динамический импорт

```js
const module = await import('./analytics.js')
module.trackPageView()
```

`import()` возвращает Promise и позволяет загружать код по необходимости. Сборщики используют это как границу разделения bundle.

## Браузер и Node.js

В браузере модуль подключается так:

```html
<script type="module" src="/src/main.js"></script>
```

Модули выполняются в strict mode и имеют собственную область видимости. В Node.js ESM обычно включается расширением `.mjs` или полем `"type": "module"` в `package.json`. Старый формат Node.js `require`/`module.exports` называется CommonJS; смешивать форматы без понимания правил совместимости не стоит.

## Организация

- модуль должен иметь ясную ответственность;
- избегайте циклических импортов;
- не выполняйте неожиданные побочные эффекты при импорте;
- зависимости между слоями направляйте от конкретных деталей к устойчивым интерфейсам проекта.
