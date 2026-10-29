import { apiClient } from '@/api/client'
import type { AuthToken, User } from '@/interfaces/auth'

// API авторизации ожидает данные формы, а не JSON.
export async function login(username: string, password: string): Promise<AuthToken> {
  const form = new URLSearchParams({ username, password })

  const response = await apiClient.post<AuthToken>('/api/v1/auth/login', form, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })

  return response.data
}

// Получает пользователя, которому принадлежит переданный JWT.
export async function getCurrentUser(token: string): Promise<User> {
  const response = await apiClient.get<User>('/api/v1/users/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  return response.data
}
