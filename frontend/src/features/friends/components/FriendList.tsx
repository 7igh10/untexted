import type { UserPublic } from '../../../api/types'

interface FriendListProps {
  friends: UserPublic[]
}

export function FriendList({ friends }: FriendListProps) {
  if (friends.length === 0) {
    return <p className="friends-empty">no friends yet</p>
  }

  return (
    <ul className="friend-list">
      {friends.map((friend) => (
        <li className="friend-item" key={friend.id}>
          <div className="user-identity">
            <strong className="user-identity__primary">{friend.display_name}</strong>
            <span className="user-identity__secondary">{friend.username}</span>
          </div>
        </li>
      ))}
    </ul>
  )
}
