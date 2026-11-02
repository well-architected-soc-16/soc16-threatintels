import { useAuth } from './auth/useAuth'
import { LoginPage } from './components/LoginPage'
import { Shell } from './components/Shell'

function App() {
  const { user } = useAuth()
  return user === null ? <LoginPage /> : <Shell />
}

export default App
