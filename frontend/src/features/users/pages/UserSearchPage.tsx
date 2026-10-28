import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../../hooks/useAuth'
import { searchUsers } from '../../../api/users'
import { listFriends, listIncomingFriendRequests, listOutgoingFriendRequests, sendFriendRequest, acceptFriendRequest, rejectFriendRequest } from '../../../api/friends'
import { ApiError } from '../../../api/client'
import { UserSearchForm } from '../components/UserSearchForm'
import { UserSearchResults } from '../components/UserSearchResults'

type RelationshipStatus =
  | 'loading'
  | 'unavailable'
  | 'friends'
  | 'request sent'
  | 'incoming'
  | 'add friend'
  | 'sending'
  | 'already friends'
  | 'request pending'
  | 'request rejected'
  | 'could not send request'

export function UserSearchPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [users, setUsers] = useState<Awaited<ReturnType<typeof searchUsers>>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [relationshipStatuses, setRelationshipStatuses] = useState<Record<string, RelationshipStatus>>({})
  const [relationshipLoading, setRelationshipLoading] = useState(true)
  const [relationshipError, setRelationshipError] = useState<string | null>(null)
  const [activeUserId, setActiveUserId] = useState<string | null>(null)
  const [incomingRequestIds, setIncomingRequestIds] = useState<Record<string, string>>({})

  useEffect(() => {
    let isMounted = true

    async function loadRelationships() {
      setRelationshipLoading(true)
      setRelationshipError(null)

      try {
        const [friends, incoming, outgoing] = await Promise.all([
          listFriends(),
          listIncomingFriendRequests(),
          listOutgoingFriendRequests(),
        ])

        if (!isMounted) {
          return
        }

        const statuses: Record<string, RelationshipStatus> = {}
        const incomingIds: Record<string, string> = {}

        for (const friend of friends) {
          statuses[friend.id] = 'friends'
        }
        for (const request of outgoing) {
          statuses[request.recipient.id] = 'request sent'
        }
        for (const request of incoming) {
          statuses[request.requester.id] = 'incoming'
          incomingIds[request.requester.id] = request.id
        }

        setRelationshipStatuses(statuses)
        setIncomingRequestIds(incomingIds)
      } catch (err) {
        if (!isMounted) {
          return
        }
        if (err instanceof Error && err.message === 'Not authenticated') {
          try {
            await logout()
          } catch {
            // The session is already invalid; navigation is still required.
          }
          navigate('/login', { replace: true })
          return
        }
        setRelationshipError(err instanceof Error ? err.message : 'Unable to load relationship status')
      } finally {
        if (isMounted) {
          setRelationshipLoading(false)
        }
      }
    }

    void loadRelationships()

    return () => {
      isMounted = false
    }
  }, [logout, navigate])

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

  async function handleAddFriend(user: { id: string; username: string }) {
    if (relationshipLoading || relationshipError) {
      return
    }

    setActiveUserId(user.id)
    setRelationshipStatuses((current) => ({ ...current, [user.id]: 'sending' }))

    try {
      const request = await sendFriendRequest({ username: user.username })
      setRelationshipStatuses((current) => ({
        ...current,
        [user.id]: request.status === 'accepted' ? 'friends' : 'request sent',
      }))
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

      let status: RelationshipStatus = 'could not send request'
      if (err instanceof ApiError) {
        if (err.detail === 'Users are already friends') {
          status = 'friends'
        } else if (err.detail === 'Friend request already pending') {
          status = 'request pending'
        }
      }
      setRelationshipStatuses((current) => ({ ...current, [user.id]: status }))
    } finally {
      setActiveUserId(null)
    }
  }

  async function handleAcceptIncoming(userId: string) {
    const requestId = incomingRequestIds[userId]
    if (!requestId) {
      return
    }

    setActiveUserId(userId)
    try {
      const accepted = await acceptFriendRequest(requestId)
      setRelationshipStatuses((current) => ({
        ...current,
        [userId]: 'friends',
      }))
      if (accepted.requester.id !== userId) {
        // Keep the map keyed by the original requester.
      }
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
      setRelationshipStatuses((current) => ({ ...current, [userId]: 'could not send request' }))
    } finally {
      setActiveUserId(null)
    }
  }

  async function handleRejectIncoming(userId: string) {
    const requestId = incomingRequestIds[userId]
    if (!requestId) {
      return
    }

    setActiveUserId(userId)
    try {
      await rejectFriendRequest(requestId)
      setRelationshipStatuses((current) => ({ ...current, [userId]: 'request rejected' }))
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
      setRelationshipStatuses((current) => ({ ...current, [userId]: 'could not send request' }))
    } finally {
      setActiveUserId(null)
    }
  }

  return (
    <section className="search-card">
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
      {relationshipError ? <p className="form-error">{relationshipError}</p> : null}
      <UserSearchResults
        users={users}
        hasSearched={hasSearched}
        relationshipStatuses={relationshipStatuses}
        relationshipLoading={relationshipLoading}
        relationshipError={relationshipError}
        activeUserId={activeUserId}
        onAddFriend={handleAddFriend}
        onAcceptRequest={handleAcceptIncoming}
        onRejectRequest={handleRejectIncoming}
      />
    </section>
  )
}
