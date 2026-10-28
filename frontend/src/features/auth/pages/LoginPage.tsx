import { Link } from 'react-router-dom'

import { AuthLayout } from '../components/AuthLayout'
import { LoginForm } from '../components/LoginForm'

export function LoginPage() {
  return (
    <AuthLayout
      title="Untexted"
      subtitle="Sign in to continue"
      footer={<Link to="/register">Create an account</Link>}
    >
      <LoginForm />
    </AuthLayout>
  )
}
