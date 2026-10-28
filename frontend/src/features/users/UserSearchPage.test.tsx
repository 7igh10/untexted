import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { AuthProvider } from '../../app/providers/AuthProvider'
import { UserSearchPage } from './pages/UserSearchPage'

function makeResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const currentUser = { id: '1', username: 'alice', display_name: 'Alice', created_at: '2026-01-01T00:00:00Z' }

describe('UserSearchPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('searches and displays users', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(200, currentUser))
      .mockResolvedValueOnce(makeResponse(200, [{ id: '2', username: 'bob', display_name: 'Bob', created_at: '2026-01-02T00:00:00Z' }]))

    render(
      <MemoryRouter>
        <AuthProvider>
          <UserSearchPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'bob')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByText('Bob')).toBeInTheDocument()
      expect(screen.getByText('bob')).toBeInTheDocument()
    })
  })

  it('does not search for an empty query', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch).mockResolvedValueOnce(makeResponse(200, currentUser))

    render(
      <MemoryRouter>
        <AuthProvider>
          <UserSearchPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByText('Enter a username to search')).toBeInTheDocument()
    })
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1)
  })

  it('shows no users found', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(200, currentUser))
      .mockResolvedValueOnce(makeResponse(200, []))

    render(
      <MemoryRouter>
        <AuthProvider>
          <UserSearchPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'zzz')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByText('No users found')).toBeInTheDocument()
    })
  })

  it('shows an error when search fails', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(200, currentUser))
      .mockResolvedValueOnce(makeResponse(500, { detail: 'Could not search users' }))

    render(
      <MemoryRouter>
        <AuthProvider>
          <UserSearchPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'bob')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByText('Could not search users')).toBeInTheDocument()
    })
  })
})
