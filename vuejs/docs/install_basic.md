# Простой Vue-проект на примере vuejs/examples/simple

Установите Node.js с сайта https://nodejs.org и проверьте установку node и npm:

```sh
node -v
npm -v
```

## Установка проекта

Пошаговая интерактивная установка проекта через Vite:
```sh
npm create vite@latest app
```

Быстрая установка Vue-проекта через Vite:
```sh
npm create vite@latest app -- --template vue
```

Обновите npm:

```sh
sudo npm install -g npm@latest
```

Перейди в папку проекта и установите зависимости (для локального запуска):

```sh
npm install
```

## Структура проекта

Базовая структура находится в примере `vuejs/examples/simple`:

Папки и файлы проекта:

- `public/` - статические файлы, которые отдаются без обработки.
- `src/` - исходный код Vue-приложения.
- `index.html` - HTML-точка входа для Vite.
- `package.json` - зависимости и скрипты проекта.
- `vite.config.js` - конфигурация Vite.

Внутри src для базы проекта лучше оставить такую структуру:

- `main.js` - точка входа. Создает Vue-приложение и монтирует его в `#app`.
- `App.vue` - корневой компонент приложения.
- `style.css` - общие стили приложения, подключаются в `main.js`.
- `assets/` - локальные изображения и статические ресурсы, которые импортируются из `src`.

## Настройка проекта

### Настройка файла `vite.config.js`.

- `defineConfig(...)` - типобезопасное описание конфига Vite.
- `plugins: [vue()]` - подключение поддержки Vue Single File Components (`.vue`).

Настройте **alias** в проекте:

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'url'

// https://vite.dev/config/
export default defineConfig({
	plugins: [vue()],
	resolve: {
		alias: {
			'@': fileURLToPath(new URL('./src', import.meta.url)),
		},
	},
})
```

Настройте поведение dev-сервера Vite (для работы с Docker):

```js
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
	plugins: [
		vue(),
	],
	server: {
		host: "0.0.0.0",
		port: 5173,
		proxy: {
			"^/(api|media)": {
				target: `http://backend:8000`,
			}
		},
	},
	resolve: {
		alias: {
			'@': fileURLToPath(new URL('./src', import.meta.url)),
		},
	},
})
```

### Установка и настройка ESLint

Установите ESLint и плагины:

```sh
npm install -D eslint @eslint/js eslint-plugin-vue @vue/eslint-config-prettier
```

В папку проекта нужно добавить файл `eslint.config.js` - flat-конфиг ESLint для `.js` и `.vue`

Пример `eslint.config.js`:

```js
import vue from 'eslint-plugin-vue'
import js from '@eslint/js'
import prettier from "eslint-config-prettier";

export default [
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettier,
  {
    files: ['**/*.vue', '**/*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
    },
  },
]
```

Можно добавить `@vue/eslint-config-prettier/skip-formatting` и `skipFormatting` после `...vue.configs['flat/recommended']`, если нужно убрать конфликты форматирования между ESLint и Prettier

Добавьте команду линтера `lint` в файл `package.json` в раздел `scripts`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint ."
  }
}
```

Для прогона линтером используйте команду:

```sh
npm run lint
```

Для автоисправление части проблем испольуйзе команду:

```sh
npm run lint -- --fix
```

### Структура файла package.json

```json
{
  "name": "vue-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint ."
  },
  "dependencies": {
    "vue": "^3.5.34"
  },
  "devDependencies": {
    "@eslint/js": "^10.0.1",
    "@vitejs/plugin-vue": "^6.0.6",
    "@vue/eslint-config-prettier": "^10.2.0",
    "eslint": "^10.4.0",
    "eslint-plugin-vue": "^10.9.1",
    "vite": "^8.0.12"
  }
}
```

- `name` - имя npm-пакета проекта.
- `private: true` - запрет публикации пакета в npm.
- `type: module` - проект использует ES Modules.
- `scripts.dev` - запуск dev-сервера.
- `scripts.build` - production-сборка.
- `scripts.preview` - локальный предпросмотр сборки.
- `scripts.lint` - запуск ESLint по всему проекту.
- `dependencies.vue` - runtime-зависимость Vue.
- `devDependencies` - инструменты сборки и линтинга (Vite, ESLint, Vue ESLint plugin).

## Запуск проекта

Проект можно запустить из каталога `vuejs/examples/simple`:

```sh
npm run dev
```

Сборка production-версии:

```sh
npm run build
```

Предпросмотр собранной версии:

```sh
npm run preview
```

### Рекомендации по росту проекта

Когда приложение станет больше, удобно постепенно расширять `src`:

- `src/views/` - страницы (экраны) приложения для роутинга.
- `src/router/` - настройка маршрутов (`vue-router`).
- `src/stores/` - глобальное состояние (`pinia`).
- `src/services/` или `src/api/` - слой запросов к backend.
- `src/composables/` - переиспользуемая бизнес-логика на Composition API.
- `src/layouts/` - шаблоны страниц (например, `AuthLayout`, `MainLayout`).
- `src/types/` - типы и интерфейсы (если используете TypeScript).

Практический порядок роста:

1. Сначала вынести страницы в `views` и подключить `router`.
2. Затем выделить API-слой (`services`) и убрать запросы из компонентов.
3. После этого вынести общее состояние в `stores`.
4. Повторяющуюся логику переносить в `composables`.

Рекомендуемые правила именования и организации:

- Компоненты: `PascalCase` (`UserCard.vue`, `AppHeader.vue`).
- Страницы в `views`: `PascalCase` с суффиксом `View` (`LoginView.vue`, `ProfileView.vue`).
- Composables: префикс `use` (`useAuth.js`, `usePagination.js`).
- Stores (Pinia): формат `useXStore` в коде, файл в `camelCase` (`authStore.js`, `profileStore.js`).
- Папки фич: `kebab-case` (`user-settings`, `order-history`).
- Константы: `UPPER_SNAKE_CASE` (`API_TIMEOUT`, `DEFAULT_PAGE_SIZE`).

Практические соглашения:

- Один крупный UI-блок - один компонентный файл.
- Переиспользуемые UI-компоненты хранить в `src/components/ui`.
- Доменные компоненты хранить рядом с фичей (например, `src/features/orders/components`).
- Использовать alias `@` для импортов из `src`, чтобы избежать длинных относительных путей.
