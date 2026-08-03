import axios from 'axios'

export const API_URL = import.meta.env.VITE_API_URL ?? 'https://posts.aledev.ru'

// Общий Axios-клиент для всех запросов приложения.
export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    Accept: 'application/json',
  },
})
