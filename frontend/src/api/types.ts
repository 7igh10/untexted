export interface UserPublic {
  id: string
  username: string
  display_name: string
  created_at: string
}

export interface ApiError {
  status: number
  detail: string
}
