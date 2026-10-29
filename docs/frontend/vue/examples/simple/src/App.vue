<script setup>
import { ref } from 'vue'
import Message from './components/Message.vue'
import Temperature from './components/Temperature.vue'

const message = ref('')

const checkTemperature = (temperature) => {
  if (!Number.isFinite(temperature)) {
    message.value = 'Сначала введите температуру'
    return
  }

  if (temperature < 0) {
    message.value = `${temperature} °C — морозно. Понадобится тёплая куртка!`
  } else if (temperature < 15) {
    message.value = `${temperature} °C — прохладно. Возьмите ветровку.`
  } else if (temperature <= 25) {
    message.value = `${temperature} °C — комфортная температура.`
  } else {
    message.value = `${temperature} °C — жарко. Не забудьте воду!`
  }
}
</script>

<template>
  <!-- Шаблон компонента -->
  <main>
    <h1>Проверка температуры</h1>

    <section class="example">
      <Temperature @check="checkTemperature" />
      <Message v-if="message" :message="message" />
    </section>
  </main>
</template>

<style scoped>
/* Стили компонента.
  scoped - стили применяются только к этому компоненту
  путём добавления data-v-xxxxxx атрибута к элементам */
main {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px;
  font-family: Arial, sans-serif;
}

.example {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-direction: column;
}
</style>
