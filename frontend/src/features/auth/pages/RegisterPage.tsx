import { Link, useLocation } from 'react-router-dom'

import { AuthLayout } from '../components/AuthLayout'
import { RegisterForm } from '../components/RegisterForm'

export function RegisterPage() {
  const location = useLocation()
  const username = (location.state as { username?: string } | null)?.username

  return (
    <AuthLayout
      title="Untexted"
      subtitle="Create your account"
      footer={<Link to="/login">Already have an account?</Link>}
    >
      <RegisterForm initialUsername={username} />
    </AuthLayout>
  )
}
