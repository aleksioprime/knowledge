# Movies

Минималистичный учебный проект на Vue 3: список популярных фильмов из TMDB.

## Запуск

```bash
npm install
cp .env.example .env
```

Добавьте свой TMDB API Read Access Token (v4 auth) в `.env`:

```env
VITE_TMDB_ACCESS_TOKEN=ваш_токен
```

Затем запустите приложение:

```bash
npm run dev
```

Запросы используют Bearer-авторизацию. Переменные `VITE_*` попадают в клиентский
JavaScript. Для учебного проекта это допустимо, но в production запросы с секретами
следует выполнять через свой backend.

Проект использует API TMDB, но не одобрен и не сертифицирован TMDB.
