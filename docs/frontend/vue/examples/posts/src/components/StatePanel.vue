<script setup lang="ts">
defineProps<{
  type: 'loading' | 'error' | 'empty'
  message?: string
}>()

defineEmits<{
  retry: []
}>()

const titles = {
  loading: 'Собираем публикации…',
  error: 'Что-то пошло не так',
  empty: 'Публикаций ещё нет',
}
</script>

<template>
  <section class="state" role="status">
    <h2>{{ titles[type] }}</h2>
    <p v-if="message">{{ message }}</p>
    <button v-if="type === 'error'" type="button" @click="$emit('retry')">Попробовать снова</button>
  </section>
</template>

<style scoped>
.state {
  padding: 32px 0;
}

h2 {
  margin: 0;
  font-size: 1.25rem;
}

p {
  color: #666;
}

button {
  padding: 8px 12px;
  border: 1px solid #aaa;
  background: white;
  font: inherit;
  cursor: pointer;
}
</style>
