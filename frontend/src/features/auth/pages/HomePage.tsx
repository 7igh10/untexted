import { useAuth } from '../../../hooks/useAuth'

function formatCreatedAt(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function HomePage() {
  const { user } = useAuth()

  return (
    <section className="home-card">
        <h1>Untexted</h1>
        <p className="auth-subtitle">Welcome, {user?.display_name ?? user?.username}.</p>

      {user ? (
        <section className="profile-summary" aria-label="Current user">
          <p>
            <strong>Username:</strong> {user.username}
          </p>
          <p>
            <strong>Display name:</strong> {user.display_name}
          </p>
          <p>
            <strong>Member since:</strong> {formatCreatedAt(user.created_at)}
          </p>
        </section>
      ) : null}

      </section>
  )
}
