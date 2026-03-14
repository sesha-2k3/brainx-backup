// Sidebar.jsx — Collapsible left navigation

import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../../context/ThemeContext'

// Icons as simple SVG components
const HomeIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
)

const ContactsIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
  </svg>
)

const TasksIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
)

const RemindersIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
)

const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

const CollapseIcon = ({ collapsed }) => (
  <svg className={`w-5 h-5 transition-transform ${collapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
  </svg>
)

const SettingsIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const SunIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
)

const MoonIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
  </svg>
)

const navItems = [
  { path: '/', label: 'Home', icon: HomeIcon },
  { path: '/contacts', label: 'Contacts', icon: ContactsIcon },
  { path: '/tasks', label: 'Tasks', icon: TasksIcon },
  { path: '/reminders', label: 'Reminders', icon: RemindersIcon },
  { path: '/search', label: 'Search', icon: SearchIcon },
]

function Sidebar({ collapsed, onToggle }) {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  return (
    <aside 
      className={`
        fixed left-0 top-0 h-full z-40
        bg-surface border-r border-default
        flex flex-col
        transition-all duration-200 ease-in-out
        ${collapsed ? 'w-16' : 'w-60'}
      `}
      style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center space-x-3">
          {/* BrainX Logo - simplified X from the uploaded image */}
          <div className="w-8 h-8 flex-shrink-0">
            <svg viewBox="0 0 32 32" className="w-full h-full">
              <path d="M8 4 L16 12 L16 4 L24 12 L24 4" fill="#C43B3B" />
              <path d="M24 4 L16 12 L24 12 L16 20 L24 20" fill="#3B5DC9" />
              <path d="M8 28 L16 20 L16 28 L8 20 L8 28" fill="#2D8F4E" />
              <path d="M24 28 L16 20 L24 20 L16 12 L24 12" fill="#D4A03B" />
            </svg>
          </div>
          {!collapsed && (
            <span className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
              BrainX
            </span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {navItems.map(({ path, label, icon: Icon }) => (
            <li key={path}>
              <NavLink
                to={path}
                className={({ isActive }) => `
                  flex items-center px-3 py-2.5 rounded-lg
                  transition-colors duration-150
                  ${isActive 
                    ? 'bg-primary text-white' 
                    : 'hover:bg-secondary text-secondary hover:text-default'
                  }
                  ${collapsed ? 'justify-center' : 'space-x-3'}
                `}
                style={({ isActive }) => ({
                  backgroundColor: isActive ? 'var(--color-primary)' : undefined,
                  color: isActive ? 'white' : 'var(--color-text-secondary)',
                })}
                title={collapsed ? label : undefined}
              >
                <Icon />
                {!collapsed && <span className="font-medium">{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>

        {/* Recent Searches - only when expanded */}
        {!collapsed && (
          <div className="mt-6 px-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-muted)' }}>
              Recent
            </h3>
            <ul className="space-y-1">
              {['Investors this month', 'Follow-ups due'].map((search, i) => (
                <li key={i}>
                  <button 
                    className="w-full text-left text-sm py-1.5 px-2 rounded hover:bg-secondary truncate"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {search}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </nav>

      {/* Bottom section */}
      <div className="p-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={`
            w-full flex items-center px-3 py-2.5 rounded-lg
            hover:bg-secondary transition-colors
            ${collapsed ? 'justify-center' : 'space-x-3'}
          `}
          style={{ color: 'var(--color-text-secondary)' }}
          title={collapsed ? (theme === 'dark' ? 'Light mode' : 'Dark mode') : undefined}
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          {!collapsed && (
            <span className="font-medium">
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </span>
          )}
        </button>

        {/* Collapse toggle */}
        <button
          onClick={onToggle}
          className={`
            w-full flex items-center px-3 py-2.5 rounded-lg
            hover:bg-secondary transition-colors mt-1
            ${collapsed ? 'justify-center' : 'space-x-3'}
          `}
          style={{ color: 'var(--color-text-secondary)' }}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <CollapseIcon collapsed={collapsed} />
          {!collapsed && <span className="font-medium">Collapse</span>}
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
