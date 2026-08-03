<script setup>
import { onMounted, ref } from 'vue'
import MovieList from './components/MovieList.vue'
import Search from './components/Search.vue'

const token = import.meta.env.VITE_TMDB_ACCESS_TOKEN
const movies = ref([])
const isLoading = ref(true)
const error = ref('')

const API_ENDPOINT = 'https://api.themoviedb.org'

async function loadMovies(query = '') {
  isLoading.value = true
  error.value = ''

  try {
    const params = new URLSearchParams({
      language: 'ru-RU',
    })

    if (query) params.set('query', query)

    const headers = new Headers({
      Authorization: `Bearer ${token}`,
    })

    const path = query ? '/3/search/movie' : '/3/movie/popular'
    const response = await fetch(`${API_ENDPOINT}${path}?${params.toString()}`, { headers })

    if (!response.ok) throw new Error('Не удалось загрузить фильмы')

    const data = await response.json()
    movies.value = data.results
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadMovies()
})
</script>

<template>
  <main>
    <h1>Фильмы</h1>

    <Search @search="loadMovies" @reset="loadMovies" />

    <p v-if="isLoading">Загрузка…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="!movies.length">Ничего не найдено</p>
    <MovieList v-else :movies="movies" />
  </main>
</template>

<style scoped>
main {
  width: min(100% - 32px, 1100px);
  margin: 0 auto;
  padding: 40px 0;
}

h1 {
  margin: 0 0 28px;
  font-size: 2rem;
}

.error {
  color: #a22;
}
</style>
