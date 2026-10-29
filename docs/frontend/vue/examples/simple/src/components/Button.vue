<script setup>
</script>

<template>
  <button type="button" >
    <span class="button-icon">
      <slot name="icon" />
    </span>

    <span class="button-text">
      <slot name="text" />
    </span>
  </button>
</template>

<style scoped>
button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: white;
  background-color: #42b883;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

button:hover {
  background-color: #369f72;
}

.button-icon {
  display: inline-flex;
}
</style>
