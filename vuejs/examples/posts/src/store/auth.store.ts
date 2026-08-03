import { ref } from 'vue'
import { defineStore } from 'pinia'
import { isAxiosError } from 'axios'

import { getCurrentUser, login as loginRequest } from '@/api/auth'
import type { User } from '@/interfaces/auth'

export const TOKEN_KEY = 'posts_access_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref(localStorage.getItem(TOKEN_KEY) ?? '')
  const isLoading = ref(false)
  const error = ref('')

  function clearError() {
    error.value = ''
  }

  function logout() {
    user.value = null
    token.value = ''
    error.value = ''
    localStorage.removeItem(TOKEN_KEY)
  }

  async function login(username: string, password: string) {
    isLoading.value = true
    error.value = ''

    try {
      const authToken = await loginRequest(username, password)

      token.value = authToken.access_token
      localStorage.setItem(TOKEN_KEY, token.value)

      user.value = await getCurrentUser(token.value)
      return true
    } catch (requestError) {
      logout()

      if (isAxiosError(requestError) && [400, 401].includes(requestError.response?.status ?? 0)) {
        error.value = 'Неверный логин или пароль'
      } else {
        error.value = 'Не удалось выполнить вход'
      }

      return false
    } finally {
      isLoading.value = false
    }
  }

  // Восстанавливает пользователя после перезагрузки страницы.
  async function restoreSession() {
    if (!token.value || user.value) return

    isLoading.value = true

    try {
      user.value = await getCurrentUser(token.value)
    } catch {
      logout()
    } finally {
      isLoading.value = false
    }
  }

  return {
    user,
    token,
    isLoading,
    error,
    login,
    logout,
    restoreSession,
    clearError,
  }
})
