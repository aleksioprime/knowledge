Установите Node.js с сайта https://nodejs.org и проверьте установку:

```sh
node -v
npm -v
```

Создайте новый проект Vite + Vue 3:

```sh
npm create vite@latest app -- --template vue
```

Обновите npm:

```sh
sudo npm install -g npm@latest
```

Перейди в папку проекта и установи зависимости (для локального запуска):

```sh
npm install
```

Папку `node_modules` и файл `package-lock.json`  не выгружать в репозиторий и не включать в образ Docker

Настрой **alias** в `vite.config.js`

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

Настрой поведение dev-сервера Vite (для работы с Docker):

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

Запусти dev-сервер для проверки:

```sh
npm run dev
```
