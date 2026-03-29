// src/App.jsx
import { Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import HomePage from './pages/HomePage'
import AddContactPage from './pages/AddContactPage'
import ContactsPage from './pages/ContactsPage'
import ContactDetailPage from './pages/ContactDetailPage'
import TasksPage from './pages/TasksPage'
import RemindersPage from './pages/RemindersPage'
import SearchPage from './pages/SearchPage'

// Wrap any route in <ProtectedRoute> to require login.
// The Layout (sidebar, nav) is only rendered for authenticated pages.
function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ErrorBoundary>
          <Routes>
            {/* ── Public routes (no layout, no auth required) ── */}
            <Route path="/login"    element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* ── Protected routes (require login, rendered inside Layout) ── */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/"               element={<HomePage />} />
                      <Route path="/add-contact"    element={<AddContactPage />} />
                      <Route path="/contacts"       element={<ContactsPage />} />
                      <Route path="/contacts/:id"   element={<ContactDetailPage />} />
                      <Route path="/tasks"          element={<TasksPage />} />
                      <Route path="/reminders"      element={<RemindersPage />} />
                      <Route path="/search"         element={<SearchPage />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </ErrorBoundary>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
