<script setup lang="ts">
import PostCard from '@/components/PostCard.vue'
import type { Post } from '@/interfaces/post'

// Список не загружает данные самостоятельно, а только получает их от App.vue.
defineProps<{
  posts: Post[]
}>()
</script>

<template>
  <section aria-label="Публикации">
    <!-- Уникальный id помогает Vue правильно переиспользовать элементы списка. -->
    <PostCard v-for="post in posts" :key="post.id" :post="post" />
  </section>
</template>
