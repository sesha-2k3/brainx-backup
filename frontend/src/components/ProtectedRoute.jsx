// components/ProtectedRoute.jsx
// Wrap any <Route> element with this to require authentication.
//
// Usage in App.jsx:
//   <Route path="/contacts" element={<ProtectedRoute><ContactsPage /></ProtectedRoute>} />

import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/authContext'

export default function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  // While we're checking the stored token, render nothing (or a spinner).
  // This prevents a flash-redirect to /login on hard refresh.
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-app">
        <div className="w-6 h-6 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    )
  }

  if (!user) {
    // Pass the attempted URL so we can redirect back after login
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
