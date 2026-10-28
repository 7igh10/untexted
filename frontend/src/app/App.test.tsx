import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import App from './App'

function makeResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the login screen for an unauthenticated user', async () => {
    vi.mocked(fetch).mockResolvedValue(makeResponse(401, { detail: 'Not authenticated' }))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Untexted' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    })
  })

  it('shows the home screen for an authenticated user', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeResponse(200, { id: '1', username: 'alice', display_name: 'Alice', created_at: '2026-01-01T00:00:00Z' }),
    )

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Welcome, Alice.')).toBeInTheDocument()
    })
  })
})
