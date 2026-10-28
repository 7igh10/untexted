import { createContext } from 'react'
import type { UserPublic } from '../../api/types'

export interface AuthContextValue {
  user: UserPublic | null
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, displayName: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
