import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../../hooks/useAuth'
import { searchUsers } from '../../../api/users'
import { UserSearchForm } from '../components/UserSearchForm'
import { UserSearchResults } from '../components/UserSearchResults'

export function UserSearchPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [users, setUsers] = useState<Awaited<ReturnType<typeof searchUsers>>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedQuery = query.trim()

    if (normalizedQuery === '') {
      setError('Enter a username to search')
      setUsers([])
      setHasSearched(false)
      return
    }

    if (normalizedQuery.length > 32) {
      setError('Search query must be at most 32 characters')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const results = await searchUsers(normalizedQuery)
      setUsers(results)
      setHasSearched(true)
    } catch (err) {
      if (err instanceof Error && err.message === 'Not authenticated') {
        try {
          await logout()
        } catch {
          // The session is already invalid; navigation is still required.
        }
        navigate('/login', { replace: true })
        return
      }

      setUsers([])
      setHasSearched(true)
      setError(err instanceof Error ? err.message : 'Unable to search users')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="auth-card">
        <h1>Find users</h1>
        <p className="auth-subtitle">Search by username</p>

        <UserSearchForm
          query={query}
          isLoading={isLoading}
          error={error}
          onQueryChange={setQuery}
          onSubmit={handleSubmit}
        />

        {isLoading ? <p className="search-status">Searching...</p> : null}
        <UserSearchResults users={users} hasSearched={hasSearched} />
      </section>
  )
}
