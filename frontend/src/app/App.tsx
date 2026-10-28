import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from './providers/AuthProvider'
import { AppRouter } from './router'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </AuthProvider>
  )
}
