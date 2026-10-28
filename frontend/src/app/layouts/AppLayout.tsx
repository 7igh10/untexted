import { useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '../../hooks/useAuth'
import { AppNavigation } from '../../components/navigation/AppNavigation'
import { Logo } from '../../components/brand/Logo'

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      // Keep the session unchanged if logout fails.
    }
  }

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <Logo />
        <AppNavigation />
        <div className="app-credits">
          <a href="https://github.com/7igh10/untexted" target="_blank" rel="noopener noreferrer">
            credits
          </a>
        </div>
      </aside>

      <header className="app-header">
        <button type="button" className="auth-button header-action" onClick={handleLogout}>
          log out
        </button>
      </header>

      <main className="app-content">{children}</main>
    </div>
  )
}
