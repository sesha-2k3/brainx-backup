// BottomNav.jsx — Mobile bottom tab navigation

import { NavLink } from 'react-router-dom'

const HomeIcon = ({ active }) => (
  <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 0 : 2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
)

const ContactsIcon = ({ active }) => (
  <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 0 : 2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const TasksIcon = ({ active }) => (
  <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 0 : 2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
)

const SearchIcon = ({ active }) => (
  <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 0 : 2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

const PlusIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
  </svg>
)

const navItems = [
  { path: '/', label: 'Home', icon: HomeIcon },
  { path: '/contacts', label: 'Contacts', icon: ContactsIcon },
  { path: '/tasks', label: 'Tasks', icon: TasksIcon },
  { path: '/search', label: 'Search', icon: SearchIcon },
]

function BottomNav({ onCaptureClick }) {
  return (
    <nav 
      className="fixed bottom-0 left-0 right-0 z-50 lg:hidden border-t safe-area-pb"
      style={{ 
        backgroundColor: 'var(--color-surface)', 
        borderColor: 'var(--color-border)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)'
      }}
    >
      <div className="flex items-center justify-around h-16">
        {navItems.slice(0, 2).map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className="flex flex-col items-center justify-center w-16 h-full"
          >
            {({ isActive }) => (
              <>
                <span style={{ color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
                  <Icon active={isActive} />
                </span>
                <span 
                  className="text-xs mt-1 font-medium"
                  style={{ color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)' }}
                >
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}

        {/* Center Add Button */}
        <button
          onClick={onCaptureClick}
          className="flex items-center justify-center w-14 h-14 rounded-full -mt-6 shadow-lg"
          style={{ backgroundColor: 'var(--color-primary)' }}
        >
          <span className="text-white">
            <PlusIcon />
          </span>
        </button>

        {navItems.slice(2).map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className="flex flex-col items-center justify-center w-16 h-full"
          >
            {({ isActive }) => (
              <>
                <span style={{ color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
                  <Icon active={isActive} />
                </span>
                <span 
                  className="text-xs mt-1 font-medium"
                  style={{ color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)' }}
                >
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

export default BottomNav
