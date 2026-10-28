import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../../hooks/useAuth'

export function HomePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      // Keep the session state unchanged if logout fails.
    }
  }

  return (
    <main className="app-shell">
      <h1>Untexted</h1>
      <p>Welcome, {user?.display_name ?? user?.username}.</p>
      <button type="button" onClick={handleLogout}>
        Log out
      </button>
    </main>
  )
}
