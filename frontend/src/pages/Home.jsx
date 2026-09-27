import { Navigate } from 'react-router-dom'
import Login from './Login'
import { getToken } from '../lib/api'

// Home doubles as the application's initial login page: authenticated users
// are sent straight to the dashboard, everyone else sees the login form.
function Home() {
  if (getToken()) {
    return <Navigate to="/dashboard" replace />
  }
  return <Login />
}

export default Home
