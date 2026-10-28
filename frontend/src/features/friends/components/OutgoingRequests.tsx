import type { FriendRequestPublic } from '../../../api/types'

interface OutgoingRequestsProps {
  requests: FriendRequestPublic[]
}

export function OutgoingRequests({ requests }: OutgoingRequestsProps) {
  if (requests.length === 0) {
    return <p className="friends-empty">no outgoing requests</p>
  }

  return (
    <ul className="friend-request-list">
      {requests.map((request) => (
        <li className="friend-request-item" key={request.id}>
          <div className="user-identity">
            <strong className="user-identity__primary">{request.recipient.display_name}</strong>
            <span className="user-identity__secondary">{request.recipient.username}</span>
          </div>
          <span className="friend-request-status">pending</span>
        </li>
      ))}
    </ul>
  )
}
