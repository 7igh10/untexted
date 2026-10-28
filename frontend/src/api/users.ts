import { apiRequest } from './client'
import type { UserPublic } from './types'

export function searchUsers(query: string) {
  const normalizedQuery = query.trim()
  return apiRequest<UserPublic[]>(
    `/users/search?q=${encodeURIComponent(normalizedQuery)}`,
  )
}
