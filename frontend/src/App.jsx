// App: Main application component with routing and layout

import { Routes, Route, NavLink } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ContactsPage from './pages/ContactsPage'
import ContactDetailPage from './pages/ContactDetailPage'
import TasksPage from './pages/TasksPage'
import SearchPage from './pages/SearchPage'
import RemindersPage from './pages/RemindersPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            <span className="font-semibold text-lg text-gray-800">BrainX</span>
            <div className="flex space-x-6">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"
                }
              >
                Add
              </NavLink>
              <NavLink
                to="/contacts"
                className={({ isActive }) =>
                  isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"
                }
              >
                Contacts
              </NavLink>
              <NavLink
                to="/tasks"
                className={({ isActive }) =>
                  isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"
                }
              >
                Tasks
              </NavLink>
              <NavLink
                to="/reminders"
                className={({ isActive }) =>
                  isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"
                }
              >
                Reminders
              </NavLink>
              <NavLink
                to="/search"
                className={({ isActive }) =>
                  isActive ? "text-blue-600 font-medium" : "text-gray-600 hover:text-gray-900"
                }
              >
                Search
              </NavLink>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/contacts/:id" element={<ContactDetailPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/reminders" element={<RemindersPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
