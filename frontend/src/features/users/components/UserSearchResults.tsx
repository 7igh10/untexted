import type { UserPublic } from '../../../api/types'

interface UserSearchResultsProps {
  users: UserPublic[]
  hasSearched: boolean
}

export function UserSearchResults({ users, hasSearched }: UserSearchResultsProps) {
  if (users.length > 0) {
    return (
      <ul className="search-results">
        {users.map((user) => (
          <li className="search-result" key={user.id}>
            <strong>{user.display_name}</strong>
            <span>{user.username}</span>
          </li>
        ))}
      </ul>
    )
  }

  if (hasSearched) {
    return <p className="search-empty">No users found</p>
  }

  return null
}
