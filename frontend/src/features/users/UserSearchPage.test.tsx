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
const bob = { id: '2', username: 'bob', display_name: 'Bob', created_at: '2026-01-02T00:00:00Z' }

function mockFetch(handlers: Record<string, (init?: RequestInit) => Response>) {
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : String(input)
    const method = init?.method ?? 'GET'
    const path = url.split('?')[0]
    const handler = handlers[`${method} ${path}`]
    if (handler) {
      return handler(init)
    }
    if (path.endsWith('/users/me')) {
      return makeResponse(200, currentUser)
    }
    return makeResponse(404, { detail: 'Not found' })
  })
}

describe('UserSearchPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('searches and displays users', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, [bob]),
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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
    mockFetch({
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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
    expect(vi.mocked(fetch).mock.calls.length).toBeGreaterThanOrEqual(4)
  })

  it('shows no users found', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, []),
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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
    mockFetch({
      'GET /api/users/search': () => makeResponse(500, { detail: 'Could not search users' }),
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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

  it('shows unavailable status when relationship loading fails', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, [bob]),
      'GET /api/friends': () => makeResponse(500, { detail: 'Could not load friends' }),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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
      expect(screen.getByText('Could not load friends')).toBeInTheDocument()
    })
  })

  it('restores request sent status after reload', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, [bob]),
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, [
        {
          id: 'request-1',
          requester: currentUser,
          recipient: bob,
          status: 'pending',
          created_at: '2026-01-03T00:00:00Z',
          updated_at: '2026-01-03T00:00:00Z',
        },
      ]),
    })

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
      expect(screen.getByText('request sent')).toBeInTheDocument()
    })
  })

  it('shows friends status when users are already friends', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, [bob]),
      'GET /api/friends': () => makeResponse(200, [bob]),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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
      expect(screen.getByText('friends')).toBeInTheDocument()
    })
  })

  it('shows incoming request actions', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, [bob]),
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, [
        {
          id: 'request-1',
          requester: bob,
          recipient: currentUser,
          status: 'pending',
          created_at: '2026-01-03T00:00:00Z',
          updated_at: '2026-01-03T00:00:00Z',
        },
      ]),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
    })

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
      expect(screen.getByRole('button', { name: 'accept' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'reject' })).toBeInTheDocument()
    })
  })

  it('shows friends status after a mutual request is auto-accepted', async () => {
    const user = userEvent.setup()
    mockFetch({
      'GET /api/users/search': () => makeResponse(200, [bob]),
      'GET /api/friends': () => makeResponse(200, []),
      'GET /api/friends/requests/incoming': () => makeResponse(200, []),
      'GET /api/friends/requests/outgoing': () => makeResponse(200, []),
      'POST /api/friends/requests': () => makeResponse(200, {
        id: 'request-1',
        requester: bob,
        recipient: currentUser,
        status: 'accepted',
        created_at: '2026-01-03T00:00:00Z',
        updated_at: '2026-01-03T00:00:00Z',
      }),
    })

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
      expect(screen.getByRole('button', { name: 'add friend' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'add friend' }))

    await waitFor(() => {
      expect(screen.getByText('friends')).toBeInTheDocument()
    })
  })
})
