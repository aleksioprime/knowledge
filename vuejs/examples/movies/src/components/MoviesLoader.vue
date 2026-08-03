<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  loading: Boolean,
  hasMore: Boolean,
  error: String,
})

const emit = defineEmits(['load', 'retry'])
const trigger = ref(null)

let observer = null

onMounted(() => {
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting && props.hasMore && !props.loading && !props.error) {
        emit('load')
      }
    },
    { rootMargin: '300px' },
  )

  observer.observe(trigger.value)
})

onBeforeUnmount(() => observer.disconnect())
</script>

<template>
  <div ref="trigger" class="movies-loader" role="status">
    <template v-if="error">
      <p>{{ error }}</p>
      <button type="button" @click="$emit('retry')">Попробовать снова</button>
    </template>
    <p v-else-if="loading">Загрузка…</p>
    <p v-else-if="!hasMore">Все фильмы загружены</p>
  </div>
</template>

<style scoped>
.movies-loader {
  min-height: 80px;
  padding-top: 24px;
  color: #666;
  text-align: center;
}

button {
  padding: 8px 12px;
  border: 1px solid #bbb;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}
</style>
