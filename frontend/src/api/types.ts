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


export interface FriendRequestPublic {
  id: string
  requester: UserPublic
  recipient: UserPublic
  status: 'pending' | 'accepted' | 'rejected'
  created_at: string
  updated_at: string
}
