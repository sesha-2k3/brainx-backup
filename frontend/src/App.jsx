// src/App.jsx
import { Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import HomePage from './pages/HomePage'
import AddContactPage from './pages/AddContactPage'
import ContactsPage from './pages/ContactsPage'
import ContactDetailPage from './pages/ContactDetailPage'
import TasksPage from './pages/TasksPage'
import RemindersPage from './pages/RemindersPage'
import SearchPage from './pages/SearchPage'

function App() {
  return (
    <ThemeProvider>
      <Layout>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/add-contact" element={<AddContactPage />} />
            <Route path="/contacts" element={<ContactsPage />} />
            <Route path="/contacts/:id" element={<ContactDetailPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/reminders" element={<RemindersPage />} />
            <Route path="/search" element={<SearchPage />} />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </ThemeProvider>
  )
}

export default App
