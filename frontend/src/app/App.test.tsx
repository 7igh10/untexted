import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Not authenticated' }),
      text: async () => 'Not authenticated',
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the bootstrap screen', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Untexted')).toBeInTheDocument()
    })
  })
})
