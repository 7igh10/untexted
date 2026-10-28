import type { FriendRequestPublic } from '../../../api/types'

interface IncomingRequestsProps {
  requests: FriendRequestPublic[]
  activeRequestId: string | null
  onAccept: (request: FriendRequestPublic) => void
  onReject: (request: FriendRequestPublic) => void
}

export function IncomingRequests({
  requests,
  activeRequestId,
  onAccept,
  onReject,
}: IncomingRequestsProps) {
  if (requests.length === 0) {
    return <p className="friends-empty">no incoming requests</p>
  }

  return (
    <ul className="friend-request-list">
      {requests.map((request) => {
        const isBusy = activeRequestId === request.id
        return (
          <li className="friend-request-item" key={request.id}>
            <div className="user-identity">
              <strong className="user-identity__primary">{request.requester.display_name}</strong>
              <span className="user-identity__secondary">{request.requester.username}</span>
            </div>
            <div className="friend-request-actions">
              <button type="button" className="auth-button" disabled={isBusy} onClick={() => onAccept(request)}>
                {isBusy ? 'working...' : 'accept'}
              </button>
              <button type="button" className="auth-secondary-button" disabled={isBusy} onClick={() => onReject(request)}>
                reject
              </button>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
