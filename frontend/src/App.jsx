import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { UserProvider } from './context/UserContext'
import { getToken } from './lib/api'
import { initTheme } from './lib/theme'

import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Courses from './pages/Courses'
import UploadMaterial from './pages/UploadMaterial'
import Chat from './pages/Chat'
import Agent from './pages/Agent'
import PYQs from './pages/PYQs'
import Calendar from './pages/Calendar'
import Settings from './pages/Settings'

// Unauthenticated visitors are routed to the initial login page ("/").
function RequireAuth({ children }) {
  if (!getToken()) {
    return <Navigate to="/" replace />
  }
  return children
}

// Already-authenticated users go straight to the dashboard.
function RedirectIfAuthed({ children }) {
  if (getToken()) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}

function App() {
  // Apply the saved light/dark theme before rendering routes.
  useEffect(() => {
    initTheme()
  }, [])

  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes (Home is the initial Login page) */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
          <Route path="/register" element={<RedirectIfAuthed><Register /></RedirectIfAuthed>} />

          {/* Authenticated Dashboard Routes */}
          <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="/courses" element={<RequireAuth><Courses /></RequireAuth>} />
          <Route path="/materials" element={<RequireAuth><UploadMaterial /></RequireAuth>} />
          <Route path="/upload" element={<RequireAuth><UploadMaterial /></RequireAuth>} />
          <Route path="/chat" element={<RequireAuth><Chat /></RequireAuth>} />
          <Route path="/agent" element={<RequireAuth><Agent /></RequireAuth>} />
          <Route path="/pyqs" element={<RequireAuth><PYQs /></RequireAuth>} />
          <Route path="/calendar" element={<RequireAuth><Calendar /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}

export default App
