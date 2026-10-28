import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../../hooks/useAuth'
import { validateRegisterForm } from '../validation'

export function RegisterForm({ initialUsername }: { initialUsername?: string }) {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState(initialUsername ?? '')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Partial<Record<'username' | 'display_name' | 'password', string>>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setServerError(null)

    const validationErrors = validateRegisterForm({
      username,
      display_name: displayName,
      password,
    })
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) {
      return
    }

    setIsSubmitting(true)
    try {
      await register(username, displayName, password)
      navigate('/', { replace: true })
    } catch (error) {
      if (error instanceof Error && error.message.includes('automatic login failed')) {
        navigate('/login', { replace: true, state: { username } })
        return
      }
      setServerError(error instanceof Error ? error.message : 'Unable to register')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <label>
        Username
        <input
          autoComplete="username"
          name="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          disabled={isSubmitting}
        />
      </label>
      {errors.username ? <p className="field-error">{errors.username}</p> : null}

      <label>
        Display name
        <input
          autoComplete="name"
          name="display_name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          disabled={isSubmitting}
        />
      </label>
      {errors.display_name ? <p className="field-error">{errors.display_name}</p> : null}

      <label>
        Password
        <input
          autoComplete="new-password"
          name="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={isSubmitting}
        />
      </label>
      {errors.password ? <p className="field-error">{errors.password}</p> : null}

      {serverError ? <p className="form-error">{serverError}</p> : null}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating account...' : 'Register'}
      </button>
    </form>
  )
}
