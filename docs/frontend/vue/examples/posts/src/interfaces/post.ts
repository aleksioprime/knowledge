// Краткие публичные данные автора, вложенные в каждый пост.
export interface Author {
  id: string
  username: string
}

// Полная структура одного поста из API.
export interface Post {
  id: string
  title: string
  content: string
  image_url: string | null
  author: Author
  created_at: string
  updated_at: string
}

// Ответ эндпоинта списка: текущая страница и данные пагинации.
export interface PostsResponse {
  items: Post[]
  total: number
  limit: number
  offset: number
}
