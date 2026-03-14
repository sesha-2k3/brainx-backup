// ContactsPage.jsx — Contact list with filters and reminder settings

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listContacts, setContactReminder } from '../api/client'

const CATEGORIES = ['all', 'investor', 'client', 'partner', 'friend', 'family', 'colleague', 'other']

const FREQUENCIES = [
  { value: 'none', label: 'No reminder' },
  { value: 'every_3_days', label: 'Every 3 days' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'every_2_weeks', label: 'Every 2 weeks' },
  { value: 'monthly', label: 'Monthly' },
]

// Avatar colors based on first letter
const avatarColors = {
  A: '#C43B3B', B: '#3B5DC9', C: '#2D8F4E', D: '#D4A03B',
  E: '#8B5CF6', F: '#EC4899', G: '#14B8A6', H: '#F97316',
  I: '#06B6D4', J: '#84CC16', K: '#EF4444', L: '#3B82F6',
  M: '#10B981', N: '#F59E0B', O: '#6366F1', P: '#EC4899',
  Q: '#14B8A6', R: '#F97316', S: '#8B5CF6', T: '#06B6D4',
  U: '#84CC16', V: '#EF4444', W: '#3B82F6', X: '#10B981',
  Y: '#F59E0B', Z: '#6366F1',
}

const getAvatarColor = (name) => {
  const firstLetter = (name || 'A').charAt(0).toUpperCase()
  return avatarColors[firstLetter] || '#6B7280'
}

function ContactsPage() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [category, setCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadContacts()
  }, [category])

  const loadContacts = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = category !== 'all' ? { category } : {}
      const result = await listContacts(params)
      setContacts(result.contacts || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFrequencyChange = async (contactId, frequency) => {
    try {
      await setContactReminder(contactId, frequency)
      setContacts(contacts.map(c => 
        c.id === contactId 
          ? { ...c, reminder_frequency: frequency === 'none' ? null : frequency }
          : c
      ))
    } catch (err) {
      setError(err.message)
    }
  }

  const isOverdue = (contact) => {
    if (!contact.next_reminder_at) return false
    return new Date(contact.next_reminder_at) <= new Date()
  }

  // Filter contacts by search query
  const filteredContacts = contacts.filter(contact => {
    if (!searchQuery.trim()) return true
    const query = searchQuery.toLowerCase()
    return (
      contact.name?.toLowerCase().includes(query) ||
      contact.company?.toLowerCase().includes(query) ||
      contact.email?.toLowerCase().includes(query)
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            Contacts
          </h1>
          <p className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            {contacts.length} contacts
          </p>
        </div>
        <Link
          to="/add-contact"
          className="btn-primary flex items-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>Add Contact</span>
        </Link>
      </div>

      {/* Search */}
      <div className="relative">
        <svg 
          className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search contacts..."
          className="input pl-10"
        />
      </div>

      {/* Category filter */}
      <div className="flex space-x-2 overflow-x-auto pb-2 -mx-4 px-4 lg:mx-0 lg:px-0">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`
              px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap
              transition-colors
            `}
            style={category === cat ? {
              backgroundColor: 'var(--color-primary)',
              color: 'white'
            } : {
              backgroundColor: 'var(--color-bg-secondary)',
              color: 'var(--color-text-secondary)'
            }}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div 
          className="px-4 py-3 rounded-lg"
          style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-error)' }}
        >
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div 
              key={i} 
              className="card h-20 animate-pulse"
              style={{ backgroundColor: 'var(--color-bg-secondary)' }}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && filteredContacts.length === 0 && (
        <div className="card p-12 text-center">
          <svg 
            className="w-16 h-16 mx-auto mb-4 opacity-50"
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>
            {searchQuery ? 'No contacts found' : 'No contacts yet'}
          </p>
          <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
            {searchQuery 
              ? 'Try a different search term' 
              : 'Add your first contact to get started'
            }
          </p>
          {!searchQuery && (
            <Link to="/add-contact" className="btn-primary">
              Add Contact
            </Link>
          )}
        </div>
      )}

      {/* Contact list */}
      {!loading && filteredContacts.length > 0 && (
        <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
          {filteredContacts.map(contact => (
            <div
              key={contact.id}
              className={`
                px-4 py-4 flex items-center justify-between
                transition-colors
              `}
              style={isOverdue(contact) ? { 
                backgroundColor: 'rgba(251, 191, 36, 0.1)' 
              } : {}}
            >
              <Link
                to={`/contacts/${contact.id}`}
                className="flex items-center flex-1 min-w-0"
              >
                {/* Avatar */}
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold text-white mr-3 flex-shrink-0"
                  style={{ backgroundColor: getAvatarColor(contact.name) }}
                >
                  {contact.name?.charAt(0).toUpperCase()}
                </div>

                {/* Info */}
                <div className="min-w-0">
                  <div className="flex items-center">
                    {isOverdue(contact) && (
                      <span 
                        className="w-2 h-2 rounded-full mr-2"
                        style={{ backgroundColor: 'var(--color-accent-gold)' }}
                        title="Due for catch-up"
                      />
                    )}
                    <h3 className="font-medium truncate" style={{ color: 'var(--color-text)' }}>
                      {contact.name}
                    </h3>
                  </div>
                  <p className="text-sm truncate" style={{ color: 'var(--color-text-secondary)' }}>
                    {[contact.role, contact.company].filter(Boolean).join(' at ') || 'No details'}
                  </p>
                </div>
              </Link>
              
              <div className="flex items-center space-x-3 ml-4">
                {/* Category badge */}
                {contact.category && (
                  <span 
                    className="px-2 py-1 text-xs font-medium rounded hidden sm:block"
                    style={{ 
                      backgroundColor: 'var(--color-bg-secondary)',
                      color: 'var(--color-text-secondary)'
                    }}
                  >
                    {contact.category}
                  </span>
                )}
                
                {/* Reminder frequency dropdown */}
                <select
                  value={contact.reminder_frequency || 'none'}
                  onChange={(e) => handleFrequencyChange(contact.id, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="text-sm rounded-lg px-2 py-1.5 border focus:ring-2 focus:ring-primary hidden sm:block"
                  style={{ 
                    backgroundColor: 'var(--color-surface)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text)'
                  }}
                  title="Stay in touch frequency"
                >
                  {FREQUENCIES.map(f => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
                
                {/* Arrow */}
                <svg 
                  className="w-5 h-5" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ContactsPage
