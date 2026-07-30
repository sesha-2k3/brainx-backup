// components/LogoutButton.jsx
// Drop this anywhere in your Layout/sidebar.
//
// Usage:
//   import LogoutButton from './LogoutButton'
//   <LogoutButton />                    // default: icon + label
//   <LogoutButton iconOnly />           // collapsed sidebar mode

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/authContext'

function LogoutIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" x2="9" y1="12" y2="12" />
    </svg>
  )
}

export default function LogoutButton({ iconOnly = false }) {
  const { logout, user } = useAuth()
  const navigate         = useNavigate()
  const [confirming, setConfirming] = useState(false)

  function handleClick() {
    if (!confirming) {
      // First click: ask for confirmation
      setConfirming(true)
      // Auto-cancel after 3s if user ignores it
      setTimeout(() => setConfirming(false), 3000)
      return
    }
    // Second click: actually log out
    logout()
    navigate('/login', { replace: true })
  }

  if (iconOnly) {
    return (
      <button
        onClick={handleClick}
        title={confirming ? 'Click again to confirm' : `Sign out (${user?.email})`}
        className={`p-2 rounded-lg transition-colors ${
          confirming
            ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
            : 'text-gray-500 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-700'
        }`}
      >
        <LogoutIcon />
      </button>
    )
  }

  return (
    <div className="border-t border-gray-200 dark:border-slate-700 pt-2 mt-2">
      {/* User email */}
      {user && (
        <div className="px-3 py-1.5 text-xs text-gray-400 dark:text-slate-500 truncate">
          {user.email}
        </div>
      )}

      <button
        onClick={handleClick}
        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          confirming
            ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'
            : 'text-gray-600 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-700'
        }`}
      >
        <LogoutIcon />
        {confirming ? 'Click again to sign out' : 'Sign out'}
      </button>
    </div>
  )
}