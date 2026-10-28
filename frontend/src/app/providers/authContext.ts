import { createContext } from 'react'
import type { UserPublic } from '../../api/types'

export interface AuthContextValue {
  user: UserPublic | null
  isLoading: boolean
  error: string | null
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
