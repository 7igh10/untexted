import { apiRequest } from './client'
import type { UserPublic } from './types'

export function getCurrentUser() {
  return apiRequest<UserPublic>('/users/me')
}

export function register(username: string, displayName: string, password: string) {
  return apiRequest<UserPublic>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      username,
      display_name: displayName,
      password,
    }),
  })
}

export function login(username: string, password: string) {
  return apiRequest<UserPublic>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout() {
  return apiRequest<void>('/auth/logout', { method: 'POST' })
}
