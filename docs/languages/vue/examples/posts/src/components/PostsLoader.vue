<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// Родитель сообщает, можно ли делать запрос, и передаёт ошибку последней страницы.
const props = defineProps<{
  loading: boolean
  hasMore: boolean
  error: string
}>()

// load запрашивает следующую страницу, retry повторяет запрос после ошибки.
const emit = defineEmits<{
  load: []
  retry: []
}>()

// DOM-элемент в конце списка, за которым будет следить IntersectionObserver.
const trigger = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

onMounted(() => {
  // Наблюдатель срабатывает за 200 пикселей до появления маркера на экране.
  // Благодаря этому следующая страница успевает загрузиться немного заранее.
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry?.isIntersecting && props.hasMore && !props.loading && !props.error) {
        emit('load')
      }
    },
    { rootMargin: '200px' },
  )

  if (trigger.value) observer.observe(trigger.value)
})

// При удалении компонента прекращаем наблюдение, чтобы освободить ресурсы.
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <!-- Этот блок одновременно служит маркером скролла и выводит состояние дозагрузки. -->
  <div ref="trigger" class="posts-loader" role="status">
    <template v-if="error">
      <p>{{ error }}</p>
      <button type="button" @click="$emit('retry')">Попробовать снова</button>
    </template>
    <p v-else-if="loading">Загрузка…</p>
    <p v-else-if="!hasMore">Все посты загружены</p>
  </div>
</template>

<style scoped>
.posts-loader {
  min-height: 80px;
  padding-bottom: 32px;
  color: #666;
  text-align: center;
}

button {
  padding: 8px 12px;
  border: 1px solid #aaa;
  background: white;
  font: inherit;
  cursor: pointer;
}
</style>
