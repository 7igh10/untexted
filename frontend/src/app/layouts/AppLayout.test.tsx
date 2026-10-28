import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { AuthProvider } from '../../app/providers/AuthProvider'
import { AppLayout } from './AppLayout'

function makeResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('AppLayout', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the logo, navigation and logout action', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeResponse(200, { id: '1', username: 'alice', display_name: 'Alice', created_at: '2026-01-01T00:00:00Z' }),
    )

    render(
      <MemoryRouter>
        <AuthProvider>
          <AppLayout>
            <p>Child content</p>
          </AppLayout>
        </AuthProvider>
      </MemoryRouter>,
    )

    await screen.findByText('Untexted')
    expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeInTheDocument()
    expect(screen.getByText('main')).toBeInTheDocument()
    expect(screen.getByText('search')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'log out' })).toBeInTheDocument()
    expect(screen.getByText('Child content')).toBeInTheDocument()
  })

  it('calls logout when the logout button is pressed', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(200, { id: '1', username: 'alice', display_name: 'Alice', created_at: '2026-01-01T00:00:00Z' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    render(
      <MemoryRouter>
        <AuthProvider>
          <AppLayout>
            <p>Child content</p>
          </AppLayout>
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'log out' }))

    await screen.findByText('Child content')
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining('/auth/logout'),
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })
})
