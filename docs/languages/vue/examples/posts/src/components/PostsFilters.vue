<script setup lang="ts">
defineProps<{
  postsCount: number
}>()
</script>

<template>
  <!-- Здесь позднее появятся элементы фильтрации. -->
  <section class="posts-filters" aria-label="Фильтры постов">
    <span>Всего: {{ postsCount }}</span>
  </section>
</template>

<style scoped>
.posts-filters {
  padding: 10px 12px;
  margin-bottom: 32px;
  border-radius: 4px;
  background: #f3f3f3;
  color: #666;
  font-size: 0.875rem;
}
</style>
