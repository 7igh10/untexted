import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { AuthProvider } from '../../app/providers/AuthProvider'
import { RegisterForm } from './components/RegisterForm'

function makeResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const userPayload = { id: '1', username: 'alice', display_name: 'Alice', created_at: '2026-01-01T00:00:00Z' }

describe('RegisterForm', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('registers and signs in automatically', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(401, { detail: 'Not authenticated' }))
      .mockResolvedValueOnce(makeResponse(201, userPayload))
      .mockResolvedValueOnce(makeResponse(200, userPayload))

    render(
      <MemoryRouter>
        <AuthProvider>
          <RegisterForm />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Display name'), 'Alice')
    await user.type(screen.getByLabelText('Password'), 'correct horse battery staple')
    await user.click(screen.getByRole('button', { name: 'Register' }))

    await waitFor(() => {
      expect(vi.mocked(fetch)).toHaveBeenCalledWith(
        expect.stringContaining('/auth/register'),
        expect.objectContaining({ method: 'POST', credentials: 'include' }),
      )
    })
  })

  it('shows an error when the username is taken', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(401, { detail: 'Not authenticated' }))
      .mockResolvedValueOnce(makeResponse(409, { detail: 'Username already taken' }))

    render(
      <MemoryRouter>
        <AuthProvider>
          <RegisterForm />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Display name'), 'Alice')
    await user.type(screen.getByLabelText('Password'), 'correct horse battery staple')
    await user.click(screen.getByRole('button', { name: 'Register' }))

    await waitFor(() => {
      expect(screen.getByText('Username already taken')).toBeInTheDocument()
    })
  })

  it('redirects to login when automatic login fails after registration', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeResponse(401, { detail: 'Not authenticated' }))
      .mockResolvedValueOnce(makeResponse(201, userPayload))
      .mockResolvedValueOnce(makeResponse(401, { detail: 'Invalid username or password' }))

    render(
      <MemoryRouter initialEntries={['/register']}>
        <AuthProvider>
          <RegisterForm />
        </AuthProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Display name'), 'Alice')
    await user.type(screen.getByLabelText('Password'), 'correct horse battery staple')
    await user.click(screen.getByRole('button', { name: 'Register' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Username')).toHaveValue('alice')
    })
  })
})
