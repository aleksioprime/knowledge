<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'

import LoginModal from '@/components/LoginModal.vue'
import { useAuthStore } from '@/store/auth.store'

const authStore = useAuthStore()
const router = useRouter()
const { user, isLoading, error } = storeToRefs(authStore)
const isLoginOpen = ref(false)

function openLogin() {
  authStore.clearError()
  isLoginOpen.value = true
}

async function submitLogin(credentials: { username: string; password: string }) {
  const isSuccessful = await authStore.login(credentials.username, credentials.password)

  if (isSuccessful) {
    isLoginOpen.value = false
  }
}

function logout() {
  authStore.logout()
  router.push({ name: 'all-posts' })
}
</script>

<template>
  <header class="header">
    <div class="header__top">
      <div>
        <h1>Посты</h1>
      </div>

      <div class="header__auth">
        <template v-if="user">
          <strong>{{ user.username }}</strong>
          <button type="button" @click="logout">Выйти</button>
        </template>

        <button v-else type="button" :disabled="isLoading" @click="openLogin">
          {{ isLoading ? 'Проверка…' : 'Войти' }}
        </button>
      </div>
    </div>

    <nav v-if="user" class="header__nav">
      <RouterLink :to="{ name: 'all-posts' }">Все посты</RouterLink>
      <RouterLink :to="{ name: 'my-posts' }">Мои посты</RouterLink>
    </nav>
  </header>

  <LoginModal
    v-if="isLoginOpen"
    :loading="isLoading"
    :error="error"
    @close="isLoginOpen = false"
    @submit="submitLogin"
  />
</template>

<style scoped>
.header {
  margin-bottom: 16px;
}

.header__top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #ddd;
}

h1 {
  margin: 0 0 8px;
  font-size: 2rem;
}

.header__auth {
  display: flex;
  align-items: center;
}

.header__nav {
  display: flex;
  gap: 20px;
}

.header__nav a {
  padding: 12px 0 10px;
  border-bottom: 2px solid transparent;
  color: #555;
  text-decoration: none;
}

.header__nav a.router-link-active {
  border-bottom-color: #222;
  color: #222;
}

.header__auth strong {
  margin-right: 12px;
}

button {
  padding: 8px 12px;
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
</style>
