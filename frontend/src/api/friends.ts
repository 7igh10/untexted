import { apiRequest } from './client'
import type { FriendRequestPublic, UserPublic } from './types'

export interface SendFriendRequestInput {
  username?: string
  user_id?: string
  recipient_id?: string
}

export function listFriends() {
  return apiRequest<UserPublic[]>('/friends')
}

export function listIncomingFriendRequests() {
  return apiRequest<FriendRequestPublic[]>('/friends/requests/incoming')
}

export function listOutgoingFriendRequests() {
  return apiRequest<FriendRequestPublic[]>('/friends/requests/outgoing')
}

export function sendFriendRequest(input: SendFriendRequestInput) {
  return apiRequest<FriendRequestPublic>('/friends/requests', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function acceptFriendRequest(requestId: string) {
  return apiRequest<FriendRequestPublic>(`/friends/requests/${requestId}/accept`, {
    method: 'POST',
  })
}

export function rejectFriendRequest(requestId: string) {
  return apiRequest<void>(`/friends/requests/${requestId}/reject`, {
    method: 'POST',
  })
}
