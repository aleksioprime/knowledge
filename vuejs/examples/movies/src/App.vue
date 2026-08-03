<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { getMovies } from './api/movies'
import MovieList from './components/MovieList.vue'
import MoviesLoader from './components/MoviesLoader.vue'
import Search from './components/Search.vue'

const movies = ref([])
const query = ref('')
const nextPage = ref(1)
const totalPages = ref(1)
const isLoading = ref(false)
const error = ref('')

let requestController = null

// Следующую страницу можно запросить, пока её номер не превысил total_pages от TMDB.
const hasMore = computed(() => nextPage.value <= totalPages.value)

async function loadMovies() {
  if (isLoading.value || !hasMore.value) return

  isLoading.value = true
  error.value = ''

  const controller = new AbortController()
  requestController = controller

  try {
    const data = await getMovies({
      query: query.value,
      page: nextPage.value,
      signal: controller.signal,
    })

    movies.value.push(...data.results)
    nextPage.value = data.page + 1
    totalPages.value = data.total_pages
  } catch (requestError) {
    if (requestError.name !== 'AbortError') {
      error.value = requestError.message
    }
  } finally {
    // Старый отменённый запрос не должен менять состояние нового запроса.
    if (requestController === controller) {
      isLoading.value = false
      requestController = null
    }
  }
}

// Новый поиск очищает старые результаты и начинает загрузку с первой страницы.
async function startSearch(searchQuery = '') {
  requestController?.abort()

  query.value = searchQuery
  movies.value = []
  nextPage.value = 1
  totalPages.value = 1
  isLoading.value = false
  error.value = ''

  await loadMovies()
}

onMounted(() => startSearch())
onBeforeUnmount(() => requestController?.abort())
</script>

<template>
  <main>
    <h1>Фильмы</h1>

    <Search @search="startSearch" @reset="startSearch" />

    <p v-if="isLoading && !movies.length">Загрузка…</p>
    <p v-else-if="error && !movies.length" class="error">{{ error }}</p>
    <p v-else-if="!movies.length">Ничего не найдено</p>

    <template v-else>
      <MovieList :movies="movies" />
      <MoviesLoader
        :loading="isLoading"
        :has-more="hasMore"
        :error="error"
        @load="loadMovies"
        @retry="loadMovies"
      />
    </template>
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
