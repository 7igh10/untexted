import type { UserPublic } from '../../../api/types'

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

interface UserSearchResultsProps {
  users: UserPublic[]
  hasSearched: boolean
  relationshipStatuses: Record<string, RelationshipStatus>
  relationshipLoading: boolean
  relationshipError: string | null
  activeUserId: string | null
  onAddFriend: (user: UserPublic) => void
  onAcceptRequest: (userId: string) => void
  onRejectRequest: (userId: string) => void
}

export function UserSearchResults({
  users,
  hasSearched,
  relationshipStatuses,
  relationshipLoading,
  relationshipError,
  activeUserId,
  onAddFriend,
  onAcceptRequest,
  onRejectRequest,
}: UserSearchResultsProps) {
  if (users.length > 0) {
    return (
      <ul className="search-results">
        {users.map((user) => {
          const status = relationshipLoading
            ? 'loading'
            : relationshipError
              ? 'unavailable'
              : relationshipStatuses[user.id] ?? 'add friend'
          const isBusy = activeUserId === user.id

          return (
            <li className="search-result" key={user.id}>
              <div className="search-result__identity">
                <strong className="search-result__primary">{user.display_name}</strong>
                <span className="search-result__secondary">{user.username}</span>
              </div>

              {status === 'incoming' ? (
                <div className="friend-request-actions">
                  <button
                    type="button"
                    className="auth-button"
                    disabled={isBusy}
                    onClick={() => onAcceptRequest(user.id)}
                  >
                    {isBusy ? 'working...' : 'accept'}
                  </button>
                  <button
                    type="button"
                    className="auth-secondary-button"
                    disabled={isBusy}
                    onClick={() => onRejectRequest(user.id)}
                  >
                    reject
                  </button>
                </div>
              ) : status === 'add friend' ? (
                <button
                  type="button"
                  className="auth-button"
                  disabled={isBusy}
                  onClick={() => onAddFriend(user)}
                >
                  {isBusy ? 'sending...' : status}
                </button>
              ) : (
                <span className="friend-request-status">{status}</span>
              )}
            </li>
          )
        })}
      </ul>
    )
  }

  if (hasSearched) {
    return <p className="search-empty">No users found</p>
  }

  return null
}
