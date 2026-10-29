<script setup lang="ts">
import type { Post } from '@/interfaces/post'

// Компонент получает один готовый пост и отвечает только за его отображение.
const props = defineProps<{
  post: Post
}>()

// Преобразуем ISO-дату сервера в понятную дату на русском языке.
const formattedDate = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
}).format(new Date(props.post.created_at))
</script>

<template>
  <article class="post-card">
    <p class="post-card__meta">{{ formattedDate }}</p>
    <h2>{{ props.post.title }}</h2>

    <!-- Картинки загружаются лениво, когда приближаются к видимой области. -->
    <img
      v-if="props.post.image_url"
      :src="props.post.image_url"
      :alt="props.post.title"
      loading="lazy"
    />
    <p>{{ props.post.content }}</p>
    <small>Автор: @{{ props.post.author.username }}</small>
  </article>
</template>

<style scoped>
.post-card {
  padding: 0 0 32px;
  margin-bottom: 32px;
  border-bottom: 1px solid #ddd;
}

img {
  width: 100%;
  display: block;
  max-height: 400px;
  margin: 16px 0;
  object-fit: cover;
}

.post-card__meta {
  margin: 0 0 8px;
  color: #666;
  font-size: 0.875rem;
}

h2 {
  margin: 0;
  font-size: 1.4rem;
}

p {
  line-height: 1.6;
}

small {
  color: #666;
}
</style>
