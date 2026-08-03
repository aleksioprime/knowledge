<script setup>
const model = defineModel('modelValue', {
  type: String,
  required: true,
  default: null,
})

</script>

<template>
  <input type="search" placeholder="Название фильма" v-model="model" />
</template>

<style scoped>
input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #bbb;
  border-radius: 6px;
  font: inherit;
}
</style>