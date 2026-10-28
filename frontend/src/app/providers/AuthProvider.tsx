import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { getCurrentUser, login as loginRequest, logout as logoutRequest, register as registerRequest } from '../../api/auth'
import type { UserPublic } from '../../api/types'
import { AuthContext } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    getCurrentUser()
      .then((currentUser) => {
        if (isMounted) {
          setUser(currentUser)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setUser(null)
          if (err instanceof Error && err.message !== 'Not authenticated') {
            setError(err.message)
          }
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  const login = async (username: string, password: string) => {
    setError(null)
    const currentUser = await loginRequest(username, password)
    setUser(currentUser)
  }

  const register = async (username: string, displayName: string, password: string) => {
    setError(null)
    await registerRequest(username, displayName, password)

    try {
      const currentUser = await loginRequest(username, password)
      setUser(currentUser)
    } catch (err) {
      setUser(null)
      const message =
        err instanceof Error
          ? err.message
          : 'Account created, but automatic login failed. Please sign in manually.'
      setError(message)
      const autoLoginError = new Error('Account created, but automatic login failed. Please sign in manually.')
      autoLoginError.cause = err
      throw autoLoginError
    }
  }

  const logout = async () => {
    setError(null)
    await logoutRequest()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, error, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
