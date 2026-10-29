<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  close: []
  submit: [credentials: { username: string; password: string }]
}>()

const username = ref('')
const password = ref('')

function submit() {
  emit('submit', {
    username: username.value.trim(),
    password: password.value,
  })
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="$emit('close')" @keydown.esc="$emit('close')">
      <section class="modal" role="dialog" aria-modal="true" aria-labelledby="login-title">
        <div class="modal__header">
          <h2 id="login-title">Вход</h2>
          <button class="modal__close" type="button" aria-label="Закрыть" @click="$emit('close')">
            ×
          </button>
        </div>

        <form @submit.prevent="submit">
          <label>
            Логин
            <input v-model="username" name="username" autocomplete="username" required autofocus />
          </label>

          <label>
            Пароль
            <input
              v-model="password"
              name="password"
              type="password"
              autocomplete="current-password"
              required
            />
          </label>

          <p v-if="error" class="modal__error">{{ error }}</p>

          <button type="submit" :disabled="loading">
            {{ loading ? 'Входим…' : 'Войти' }}
          </button>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgb(0 0 0 / 45%);
}

.modal {
  width: min(100%, 360px);
  padding: 24px;
  border-radius: 8px;
  background: white;
}

.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

h2 {
  margin: 0;
}

.modal__close {
  padding: 0;
  border: 0;
  background: none;
  font-size: 1.5rem;
}

form,
label {
  display: grid;
  gap: 8px;
}

form {
  gap: 16px;
}

input {
  width: 100%;
  padding: 10px;
  border: 1px solid #aaa;
  border-radius: 4px;
  font: inherit;
}

button {
  padding: 9px 14px;
  border: 1px solid #aaa;
  border-radius: 4px;
  background: white;
  font: inherit;
  cursor: pointer;
}

button:disabled {
  cursor: default;
  opacity: 0.6;
}

.modal__error {
  margin: 0;
  color: #a22;
}
</style>
