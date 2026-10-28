import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../../hooks/useAuth'
import {
  acceptFriendRequest,
  listFriends,
  listIncomingFriendRequests,
  listOutgoingFriendRequests,
  rejectFriendRequest,
} from '../../../api/friends'
import type { FriendRequestPublic, UserPublic } from '../../../api/types'
import { FriendList } from '../components/FriendList'
import { IncomingRequests } from '../components/IncomingRequests'
import { OutgoingRequests } from '../components/OutgoingRequests'

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

export function FriendsPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [friends, setFriends] = useState<UserPublic[]>([])
  const [incoming, setIncoming] = useState<FriendRequestPublic[]>([])
  const [outgoing, setOutgoing] = useState<FriendRequestPublic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null)

  const loadFriends = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const [friendsResult, incomingResult, outgoingResult] = await Promise.all([
        listFriends(),
        listIncomingFriendRequests(),
        listOutgoingFriendRequests(),
      ])
      setFriends(friendsResult)
      setIncoming(incomingResult)
      setOutgoing(outgoingResult)
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
      setError(getErrorMessage(err, 'Unable to load friends'))
    } finally {
      setIsLoading(false)
    }
  }, [logout, navigate])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadFriends()
  }, [loadFriends])

  async function handleAccept(request: FriendRequestPublic) {
    setActionError(null)
    setActiveRequestId(request.id)
    try {
      const accepted = await acceptFriendRequest(request.id)
      setIncoming((current) => current.filter((item) => item.id !== request.id))
      setFriends((current) =>
        current.some((friend) => friend.id === accepted.requester.id)
          ? current
          : [accepted.requester, ...current],
      )
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
      setActionError(getErrorMessage(err, 'Unable to accept request'))
    } finally {
      setActiveRequestId(null)
    }
  }

  async function handleReject(request: FriendRequestPublic) {
    setActionError(null)
    setActiveRequestId(request.id)
    try {
      await rejectFriendRequest(request.id)
      setIncoming((current) => current.filter((item) => item.id !== request.id))
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
      setActionError(getErrorMessage(err, 'Unable to reject request'))
    } finally {
      setActiveRequestId(null)
    }
  }

  return (
    <section className="friends-card">
      <h1>friends</h1>
      <p className="auth-subtitle">your friends and requests</p>

      {isLoading ? <p className="friends-status">Loading...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {actionError ? <p className="form-error">{actionError}</p> : null}

      {!isLoading ? (
        <>
          <section className="friends-section">
            <h2>friends</h2>
            <FriendList friends={friends} />
          </section>

          <section className="friends-section">
            <h2>incoming requests</h2>
            <IncomingRequests
              requests={incoming}
              activeRequestId={activeRequestId}
              onAccept={handleAccept}
              onReject={handleReject}
            />
          </section>

          <section className="friends-section">
            <h2>outgoing requests</h2>
            <OutgoingRequests requests={outgoing} />
          </section>
        </>
      ) : null}
    </section>
  )
}
