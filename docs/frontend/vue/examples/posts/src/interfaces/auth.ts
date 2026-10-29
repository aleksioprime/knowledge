export interface AuthToken {
  access_token: string
  token_type: string
}

export interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  created_at: string
}
