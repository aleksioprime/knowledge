<script setup>
import MovieCard from './MovieCard.vue'

defineProps({
  movies: Array,
})
</script>

<template>
  <section class="movie-list">
    <MovieCard v-for="movie in movies" :key="movie.id" :movie="movie" />
  </section>
</template>

<style scoped>
.movie-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}
</style>
