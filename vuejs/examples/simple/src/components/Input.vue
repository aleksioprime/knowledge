<script setup>
// Наивная реализация двустороннего связывания
const { value } = defineProps(['value'])

const emit = defineEmits(['input'])
const inputTemperature = (event) => {
    emit('input', Number(event.target.value))
}

// Основная реализация двустороннего связывания
// const model = defineModel('modelValue', {
//   type: Number,
//   required: true,
//   default: null,
// })

</script>

<template>
    <label for="temperature">Температура, °C</label>
    <!-- Наивная реализация двустороннего связывания -->
    <input id="temperature" type="number" placeholder="Например, 18" :value="value" @input="inputTemperature($event)" >

    <!-- Основная реализация двустороннего связывания -->
    <!-- <input id="temperature" type="number" placeholder="Например, 18" v-model="model"> -->
</template>