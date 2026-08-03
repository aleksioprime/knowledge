<script setup>
import { ref } from 'vue'
import Input from './Input.vue'
import Button from './Button.vue'

const emit = defineEmits(['search', 'reset'])
const query = ref('')

const search = () => {
  if (query.value.trim()) emit('search', query.value.trim())
}

const reset = () => {
  query.value = ''
  emit('reset')
}
</script>

<template>
  <form @submit.prevent="search">
    <Input v-model="query" />
    <Button type="submit">Поиск</Button>
    <Button @click="reset">Сбросить</Button>
  </form>
</template>

<style scoped>
form {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  margin-bottom: 28px;
}

@media (max-width: 500px) {
  form {
    grid-template-columns: 1fr 1fr;
  }

  form :first-child {
    grid-column: 1 / -1;
  }
}
</style>
