<script setup>
import { ref } from 'vue'
import Button from './Button.vue'
import Input from './Input.vue'

const emit = defineEmits(['check'])
const temperature = ref(0)

const inputTemperature = (value) => {
  temperature.value = value
}

const checkTemperature = () => {
  emit('check', temperature.value)
}
</script>

<template>
  <div class="temperature-checker">

    <Input :value="temperature" @input="inputTemperature" />

    <Button @click="checkTemperature">
      <template #icon>
        <span aria-hidden="true">🌡</span>
      </template>

      <template #text>
        Проверить температуру
      </template>
    </Button>
  </div>
</template>

<style scoped>
.temperature-checker {
  display: grid;
  gap: 8px;
  width: 100%;
}

label {
  font-weight: 600;
}

input {
  box-sizing: border-box;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #b8bec7;
  border-radius: 6px;
  font: inherit;
}

input:focus {
  border-color: #42b883;
  outline: 2px solid rgb(66 184 131 / 20%);
}
</style>