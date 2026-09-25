import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { UserProvider } from './context/UserContext'

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

function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Authenticated Dashboard Routes */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/courses" element={<Courses />} />
          <Route path="/materials" element={<UploadMaterial />} />
          <Route path="/upload" element={<UploadMaterial />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/agent" element={<Agent />} />
          <Route path="/pyqs" element={<PYQs />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}

export default App