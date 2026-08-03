const API_URL = 'https://api.themoviedb.org'
const token = import.meta.env.VITE_TMDB_ACCESS_TOKEN

// Получает одну страницу популярных фильмов или результатов поиска.
export async function getMovies({ query = '', page = 1, signal } = {}) {
  const path = query ? '/3/search/movie' : '/3/movie/popular'
  const url = new URL(path, API_URL)

  url.searchParams.set('language', 'ru-RU')
  url.searchParams.set('page', String(page))

  if (query) {
    url.searchParams.set('query', query)
  }

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    signal,
  })

  if (!response.ok) {
    throw new Error(`Не удалось загрузить фильмы (${response.status})`)
  }

  return await response.json()
}
