import { Routes, Route, NavLink } from 'react-router-dom'
import HomePage from './pages/HomePage'
import AddContactPage from './pages/AddContactPage'
import ContactsPage from './pages/ContactsPage'
import ContactDetailPage from './pages/ContactDetailPage'
import TasksPage from './pages/TasksPage'
import RemindersPage from './pages/RemindersPage'
import SearchPage from './pages/SearchPage'

function App() {
  const navLinkClass = ({ isActive }) =>
    `px-3 py-2 rounded-md text-sm font-medium ${
      isActive
        ? 'text-blue-600'
        : 'text-gray-600 hover:text-gray-900'
    }`

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            <NavLink to="/" className="text-lg font-semibold text-gray-900">
              BrainX
            </NavLink>
            <div className="flex items-center space-x-1">
              <NavLink to="/add-contact" className={navLinkClass}>
                + Contact
              </NavLink>
              <NavLink to="/" className={navLinkClass}>
                + Interaction
              </NavLink>
              <NavLink to="/contacts" className={navLinkClass}>
                Contacts
              </NavLink>
              <NavLink to="/tasks" className={navLinkClass}>
                Tasks
              </NavLink>
              <NavLink to="/reminders" className={navLinkClass}>
                Reminders
              </NavLink>
              <NavLink to="/search" className={navLinkClass}>
                Search
              </NavLink>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/add-contact" element={<AddContactPage />} />
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