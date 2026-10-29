<script setup>
const { message } = defineProps({
  message: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <output aria-live="polite">{{ message }}</output>
</template>

<style scoped>
output {
  padding: 12px;
  background-color: #f2f4f7;
  border-radius: 6px;
}
</style>
