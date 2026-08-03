import { API_URL, apiClient } from '@/api/client'
import type { Post, PostsResponse } from '@/interfaces/post'

// API возвращает относительные пути изображений, например /media/post.webp.
// Преобразуем такой путь в полный адрес, подходящий для атрибута src.
function getImageUrl(imageUrl: string | null) {
  if (!imageUrl) return null

  return new URL(imageUrl, API_URL).toString()
}

function prepareResponse(data: PostsResponse): PostsResponse {
  return {
    ...data,
    items: data.items.map((post: Post) => ({
      ...post,
      image_url: getImageUrl(post.image_url),
    })),
  }
}

// Получает одну страницу постов с сервера.
// limit — размер страницы, offset — количество пропускаемых записей.
export async function getPosts(limit = 10, offset = 0): Promise<PostsResponse> {
  const response = await apiClient.get<PostsResponse>('/api/v1/posts', {
    params: { limit, offset },
  })

  return prepareResponse(response.data)
}

// Получает посты авторизованного пользователя.
export async function getMyPosts(token: string, limit = 10, offset = 0): Promise<PostsResponse> {
  const response = await apiClient.get<PostsResponse>('/api/v1/posts/mine', {
    params: { limit, offset },
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  return prepareResponse(response.data)
}
