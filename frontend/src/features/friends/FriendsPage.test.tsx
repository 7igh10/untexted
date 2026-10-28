import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { AuthProvider } from '../../app/providers/AuthProvider'
import { FriendsPage } from './pages/FriendsPage'

function makeResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const currentUser = { id: '1', username: 'alice', display_name: 'Alice', created_at: '2026-01-01T00:00:00Z' }
const friend = { id: '2', username: 'bob', display_name: 'Bob', created_at: '2026-01-02T00:00:00Z' }
const incomingRequest = {
  id: 'request-1',
  requester: friend,
  recipient: currentUser,
  status: 'pending',
  created_at: '2026-01-03T00:00:00Z',
  updated_at: '2026-01-03T00:00:00Z',
}
const outgoingRequest = {
  id: 'request-2',
  requester: currentUser,
  recipient: friend,
  status: 'pending',
  created_at: '2026-01-04T00:00:00Z',
  updated_at: '2026-01-04T00:00:00Z',
}

describe('FriendsPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function mockLoad(friends: unknown[] = [], incoming: unknown[] = [], outgoing: unknown[] = []) {
    vi.mocked(fetch).mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : String(input)
      if (url.endsWith('/users/me')) {
        return makeResponse(200, currentUser)
      }
      if (url.endsWith('/friends')) {
        return makeResponse(200, friends)
      }
      if (url.endsWith('/friends/requests/incoming')) {
        return makeResponse(200, incoming)
      }
      if (url.endsWith('/friends/requests/outgoing')) {
        return makeResponse(200, outgoing)
      }
      return makeResponse(404, { detail: 'Not found' })
    })
  }

  it('loads and displays friends and requests', async () => {
    mockLoad([friend], [incomingRequest], [outgoingRequest])

    render(
      <MemoryRouter>
        <AuthProvider>
          <FriendsPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getAllByText('Bob').length).toBeGreaterThan(0)
    })
  })

  it('shows empty states', async () => {
    mockLoad()

    render(
      <MemoryRouter>
        <AuthProvider>
          <FriendsPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('no friends yet')).toBeInTheDocument()
      expect(screen.getByText('no incoming requests')).toBeInTheDocument()
      expect(screen.getByText('no outgoing requests')).toBeInTheDocument()
    })
  })

  it('accepts an incoming request and adds the friend', async () => {
    const user = userEvent.setup()
    mockLoad([], [incomingRequest], [])
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const url = typeof input === 'string' ? input : String(input)
      const method = init?.method ?? 'GET'
      if (url.endsWith('/users/me')) {
        return makeResponse(200, currentUser)
      }
      if (url.endsWith('/friends')) {
        return makeResponse(200, [])
      }
      if (url.endsWith('/friends/requests/incoming')) {
        return makeResponse(200, [incomingRequest])
      }
      if (url.endsWith('/friends/requests/outgoing')) {
        return makeResponse(200, [])
      }
      if (url.endsWith(`/friends/requests/${incomingRequest.id}/accept`) && method === 'POST') {
        return makeResponse(200, { ...incomingRequest, status: 'accepted' })
      }
      return makeResponse(404, { detail: 'Not found' })
    })

    render(
      <MemoryRouter>
        <AuthProvider>
          <FriendsPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getAllByText('Bob').length).toBeGreaterThan(0)
    })

    await user.click(screen.getByRole('button', { name: 'accept' }))

    await waitFor(() => {
      expect(screen.getByText('no incoming requests')).toBeInTheDocument()
      expect(screen.getAllByText('Bob').length).toBeGreaterThan(0)
    })
  })

  it('rejects an incoming request', async () => {
    const user = userEvent.setup()
    mockLoad([], [incomingRequest], [])
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const url = typeof input === 'string' ? input : String(input)
      const method = init?.method ?? 'GET'
      if (url.endsWith('/users/me')) {
        return makeResponse(200, currentUser)
      }
      if (url.endsWith('/friends')) {
        return makeResponse(200, [])
      }
      if (url.endsWith('/friends/requests/incoming')) {
        return makeResponse(200, [incomingRequest])
      }
      if (url.endsWith('/friends/requests/outgoing')) {
        return makeResponse(200, [])
      }
      if (url.endsWith(`/friends/requests/${incomingRequest.id}/reject`) && method === 'POST') {
        return new Response(null, { status: 204 })
      }
      return makeResponse(404, { detail: 'Not found' })
    })

    render(
      <MemoryRouter>
        <AuthProvider>
          <FriendsPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getAllByText('Bob').length).toBeGreaterThan(0)
    })

    await user.click(screen.getByRole('button', { name: 'reject' }))

    await waitFor(() => {
      expect(screen.getByText('no incoming requests')).toBeInTheDocument()
    })
  })

  it('shows an error when loading fails', async () => {
    vi.mocked(fetch).mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : String(input)
      if (url.endsWith('/users/me')) {
        return makeResponse(200, currentUser)
      }
      return makeResponse(500, { detail: 'Could not load friends' })
    })

    render(
      <MemoryRouter>
        <AuthProvider>
          <FriendsPage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Could not load friends')).toBeInTheDocument()
    })
  })
})
