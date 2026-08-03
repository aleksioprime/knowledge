import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getMyPosts, getPosts } from '@/api/posts'
import type { Post } from '@/interfaces/post'
import { useAuthStore } from '@/store/auth.store'

const POSTS_PER_PAGE = 5

type PageState = 'loading' | 'error' | 'empty' | null
export type PostScope = 'all' | 'mine'

export const usePostStore = defineStore('posts', () => {
  const authStore = useAuthStore()

  // State: данные и состояния, связанные со списком постов.
  const posts = ref<Post[]>([]) // Список постов, которые уже были загружены с сервера
  const total = ref(0) // Общее количество постов на сервере
  const isLoading = ref(false) // Флаг, что запрос выполняется в данный момент
  const error = ref('') // Сообщение об ошибке. Пустая строка означает отсутствие ошибки
  const scope = ref<PostScope>('all')

  // Getter: на сервере остались посты, которых ещё нет в сторе.
  const hasMore = computed(() => posts.value.length < total.value)

  // Состояние страницы до появления первого поста.
  const pageState = computed<PageState>(() => {
    if (error.value && posts.value.length === 0) return 'error'
    if (isLoading.value && posts.value.length === 0) return 'loading'
    if (posts.value.length === 0) return 'empty'

    return null
  })

  // Action используется при первой загрузке, пагинации и повторе после ошибки.
  async function loadPosts() {
    // Защищаемся от параллельных запросов и выхода за пределы списка.
    if (isLoading.value || (total.value > 0 && !hasMore.value)) return

    isLoading.value = true
    error.value = ''

    try {
      const response =
        scope.value === 'mine'
          ? await getMyPosts(authStore.token, POSTS_PER_PAGE, posts.value.length)
          : await getPosts(POSTS_PER_PAGE, posts.value.length)

      // Следующую страницу добавляем к уже загруженным постам.
      posts.value.push(...response.items)
      total.value = response.total
    } catch (requestError) {
      error.value =
        requestError instanceof Error ? requestError.message : 'Не удалось загрузить публикации'
    } finally {
      isLoading.value = false
    }
  }

  // При переключении маршрута очищаем предыдущую ленту и начинаем с первой страницы.
  async function openFeed(nextScope: PostScope) {
    if (scope.value !== nextScope) {
      scope.value = nextScope
      posts.value = []
      total.value = 0
      error.value = ''
    }

    await loadPosts()
  }

  return {
    posts,
    total,
    isLoading,
    error,
    hasMore,
    pageState,
    loadPosts,
    openFeed,
  }
})
