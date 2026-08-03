<script setup>
defineProps({
  movie: Object,
})
</script>

<template>
  <article class="movie-card">
    <img
      v-if="movie.poster_path"
      :src="`https://image.tmdb.org/t/p/w500${movie.poster_path}`"
      :alt="movie.title"
      loading="lazy"
    />
    <div v-else class="poster-placeholder">Нет постера</div>

    <div class="movie-info">
      <h2>{{ movie.title }}</h2>
      <span>{{ movie.release_date?.slice(0, 4) || '—' }} · ★ {{ movie.vote_average.toFixed(1) }}</span>
    </div>
  </article>
</template>

<style scoped>
.movie-card {
  overflow: hidden;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fff;
}

.movie-card img,
.poster-placeholder {
  display: block;
  width: 100%;
  aspect-ratio: 2 / 3;
}

.movie-card img {
  object-fit: cover;
}

.poster-placeholder {
  display: grid;
  place-items: center;
  color: #777;
  background: #e5e5e5;
}

.movie-info {
  padding: 12px;
}

.movie-info h2 {
  margin: 0 0 8px;
  font-size: 1rem;
}

.movie-info span {
  color: #777;
  font-size: 0.85rem;
}
</style>
