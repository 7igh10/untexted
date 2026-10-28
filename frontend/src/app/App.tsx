import { AuthProvider } from './providers/AuthProvider'

export default function App() {
  return (
    <AuthProvider>
      <main className="app-shell">
        <h1>Untexted</h1>
        <p>Minimal frontend bootstrap.</p>
      </main>
    </AuthProvider>
  )
}
