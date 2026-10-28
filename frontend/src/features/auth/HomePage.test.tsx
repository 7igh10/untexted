import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { AuthProvider } from '../../app/providers/AuthProvider'
import { HomePage } from './pages/HomePage'

function makeResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('displays the authenticated user profile', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeResponse(200, {
        id: '1',
        username: 'alice',
        display_name: 'Alice',
        created_at: '2026-01-01T00:00:00Z',
      }),
    )

    render(
      <MemoryRouter>
        <AuthProvider>
          <HomePage />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Welcome, Alice.')).toBeInTheDocument()
      expect(screen.getByText('Username:').parentElement).toHaveTextContent('alice')
      expect(screen.getByText('Display name:').parentElement).toHaveTextContent('Alice')
      expect(screen.getByText('Member since:')).toBeInTheDocument()
    })
  })
})
