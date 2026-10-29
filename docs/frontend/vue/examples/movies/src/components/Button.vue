<script setup>
defineProps({
  type: {
    type: String,
    default: 'button',
  },
})
</script>

<template>
  <button :type="type">
    <slot />
  </button>
</template>

<style scoped>
button {
  padding: 10px 16px;
  border: 0;
  border-radius: 6px;
  color: white;
  background: #42b883;
  cursor: pointer;
}

button:hover {
  background: #369f72;
}
</style>