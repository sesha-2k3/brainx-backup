// CommandBar.jsx — Quick search modal (Cmd+K)

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchContacts, listContacts, listTasks } from '../api/client'

function CommandBar({ isOpen, onClose }) {
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState({ contacts: [], tasks: [] })
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [recentSearches] = useState([
    'Investors this month',
    'Tasks due today',
    'Who is John?'
  ])

  // Focus input when opening
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
      setQuery('')
      setSelectedIndex(0)
    }
  }, [isOpen])

  // Search as user types
  useEffect(() => {
    if (!query.trim()) {
      setResults({ contacts: [], tasks: [] })
      return
    }

    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const searchResult = await searchContacts(query)
        setResults({
          contacts: searchResult.contacts?.slice(0, 5) || [],
          tasks: searchResult.tasks?.slice(0, 3) || [],
        })
      } catch (err) {
        console.error('Search error:', err)
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  // Keyboard navigation
  const handleKeyDown = (e) => {
    const totalItems = results.contacts.length + results.tasks.length + quickActions.length

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => (i + 1) % totalItems)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => (i - 1 + totalItems) % totalItems)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleSelect(selectedIndex)
    }
  }

  const quickActions = [
    { id: 'add-contact', label: 'Add new contact', icon: '➕', action: () => navigate('/add-contact') },
    { id: 'view-tasks', label: 'View all tasks', icon: '📋', action: () => navigate('/tasks') },
    { id: 'reminders', label: 'Check reminders', icon: '🔔', action: () => navigate('/reminders') },
  ]

  const handleSelect = (index) => {
    let currentIndex = 0

    // Check contacts
    for (const contact of results.contacts) {
      if (currentIndex === index) {
        navigate(`/contacts/${contact.id}`)
        onClose()
        return
      }
      currentIndex++
    }

    // Check tasks
    for (const task of results.tasks) {
      if (currentIndex === index) {
        navigate('/tasks')
        onClose()
        return
      }
      currentIndex++
    }

    // Check quick actions
    for (const action of quickActions) {
      if (currentIndex === index) {
        action.action()
        onClose()
        return
      }
      currentIndex++
    }
  }

  if (!isOpen) return null

  const hasResults = results.contacts.length > 0 || results.tasks.length > 0

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-50 command-overlay animate-fade-in"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-x-4 top-[20%] z-50 max-w-2xl mx-auto animate-scale-in">
        <div 
          className="rounded-xl shadow-2xl overflow-hidden"
          style={{ backgroundColor: 'var(--color-surface)' }}
        >
          {/* Search input */}
          <div className="flex items-center px-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <svg className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--color-text-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search contacts, tasks, or type a command..."
              className="w-full px-4 py-4 bg-transparent outline-none"
              style={{ color: 'var(--color-text)' }}
            />
            {loading && (
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto">
            {/* Contacts */}
            {results.contacts.length > 0 && (
              <div className="p-2">
                <div 
                  className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Contacts
                </div>
                {results.contacts.map((contact, i) => (
                  <button
                    key={contact.id}
                    onClick={() => { navigate(`/contacts/${contact.id}`); onClose() }}
                    className={`
                      w-full flex items-center px-3 py-2.5 rounded-lg text-left
                      ${selectedIndex === i ? 'bg-primary text-white' : 'hover:bg-secondary'}
                    `}
                    style={selectedIndex !== i ? { color: 'var(--color-text)' } : {}}
                  >
                    <div 
                      className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium mr-3"
                      style={{ 
                        backgroundColor: selectedIndex === i ? 'rgba(255,255,255,0.2)' : 'var(--color-primary-light)',
                        color: selectedIndex === i ? 'white' : 'var(--color-primary)'
                      }}
                    >
                      {contact.name?.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-medium">{contact.name}</div>
                      {contact.company && (
                        <div 
                          className="text-sm"
                          style={{ color: selectedIndex === i ? 'rgba(255,255,255,0.8)' : 'var(--color-text-secondary)' }}
                        >
                          {contact.company}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Tasks */}
            {results.tasks.length > 0 && (
              <div className="p-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
                <div 
                  className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Tasks
                </div>
                {results.tasks.map((task, i) => {
                  const idx = results.contacts.length + i
                  return (
                    <button
                      key={task.id}
                      onClick={() => { navigate('/tasks'); onClose() }}
                      className={`
                        w-full flex items-center px-3 py-2.5 rounded-lg text-left
                        ${selectedIndex === idx ? 'bg-primary text-white' : 'hover:bg-secondary'}
                      `}
                      style={selectedIndex !== idx ? { color: 'var(--color-text)' } : {}}
                    >
                      <span className="mr-3">📋</span>
                      <span>{task.title}</span>
                    </button>
                  )
                })}
              </div>
            )}

            {/* Quick Actions */}
            {!hasResults && (
              <div className="p-2">
                <div 
                  className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Quick Actions
                </div>
                {quickActions.map((action, i) => {
                  const idx = results.contacts.length + results.tasks.length + i
                  return (
                    <button
                      key={action.id}
                      onClick={() => { action.action(); onClose() }}
                      className={`
                        w-full flex items-center px-3 py-2.5 rounded-lg text-left
                        ${selectedIndex === idx ? 'bg-primary text-white' : 'hover:bg-secondary'}
                      `}
                      style={selectedIndex !== idx ? { color: 'var(--color-text)' } : {}}
                    >
                      <span className="mr-3">{action.icon}</span>
                      <span>{action.label}</span>
                    </button>
                  )
                })}

                {/* Recent searches */}
                {query === '' && (
                  <>
                    <div 
                      className="px-3 py-1.5 mt-4 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--color-text-muted)' }}
                    >
                      Recent Searches
                    </div>
                    {recentSearches.map((search, i) => (
                      <button
                        key={i}
                        onClick={() => setQuery(search)}
                        className="w-full flex items-center px-3 py-2 rounded-lg text-left hover:bg-secondary"
                        style={{ color: 'var(--color-text-secondary)' }}
                      >
                        <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{search}</span>
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div 
            className="flex items-center justify-between px-4 py-2 border-t text-xs"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
          >
            <div className="flex items-center space-x-4">
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">↑↓</kbd> Navigate</span>
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">↵</kbd> Select</span>
            </div>
            <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">Esc</kbd> Close</span>
          </div>
        </div>
      </div>
    </>
  )
}

export default CommandBar
