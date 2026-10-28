import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from '../hooks/useAuth'
import { HomePage } from '../features/auth/pages/HomePage'
import { AppLayout } from './layouts/AppLayout'
import { UserSearchPage } from '../features/users/pages/UserSearchPage'
import { FriendsPage } from '../features/friends/pages/FriendsPage'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { RegisterPage } from '../features/auth/pages/RegisterPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <main className="auth-page"><p>Loading session...</p></main>
  }

  if (user === null) {
    return <Navigate to="/login" replace />
  }

  return children
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <main className="auth-page"><p>Loading session...</p></main>
  }

  if (user !== null) {
    return <Navigate to="/" replace />
  }

  return children
}

export function AppRouter() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />
      <Route
        path="/friends"
        element={
          <ProtectedRoute>
            <AppLayout>
              <FriendsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/friends"
        element={
          <ProtectedRoute>
            <AppLayout>
              <FriendsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <AppLayout>
              <UserSearchPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout>
              <HomePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
