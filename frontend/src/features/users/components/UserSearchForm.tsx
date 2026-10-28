import type { FormEvent } from 'react'

interface UserSearchFormProps {
  query: string
  isLoading: boolean
  error: string | null
  onQueryChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function UserSearchForm({
  query,
  isLoading,
  error,
  onQueryChange,
  onSubmit,
}: UserSearchFormProps) {
  return (
    <form className="auth-form" onSubmit={onSubmit} noValidate>
      <label>
        Username
        <input
          name="query"
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          disabled={isLoading}
          maxLength={32}
        />
      </label>

      {error ? <p className="form-error">{error}</p> : null}

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Searching...' : 'Search'}
      </button>
    </form>
  )
}
