// RemindersPage.jsx — Contacts due for catch-up, plus upcoming reminders panel

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getDueReminders, getUpcomingReminders, markContacted } from '../api/client'

// Avatar colors
const avatarColors = {
  A: '#C43B3B', B: '#3B5DC9', C: '#2D8F4E', D: '#D4A03B',
  E: '#8B5CF6', F: '#EC4899', G: '#14B8A6', H: '#F97316',
}

const getAvatarColor = (name) => {
  const firstLetter = (name || 'A').charAt(0).toUpperCase()
  return avatarColors[firstLetter] || '#6B7280'
}

// "in 3 days" / "tomorrow" / "in 2 weeks" style formatting for a future date
const formatUpcoming = (dateStr) => {
  if (!dateStr) return null
  const target = new Date(dateStr)
  const now = new Date()
  const days = Math.ceil((target - now) / (1000 * 60 * 60 * 24))

  if (days <= 0) return 'today'
  if (days === 1) return 'tomorrow'
  if (days < 14) return `in ${days} days`
  const weeks = Math.round(days / 7)
  return `in ${weeks} week${weeks !== 1 ? 's' : ''}`
}

function RemindersPage() {
  const [contacts, setContacts] = useState([])
  const [upcoming, setUpcoming] = useState([])
  const [loading, setLoading] = useState(true)
  const [upcomingLoading, setUpcomingLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadReminders()
    loadUpcoming()
  }, [])

  const loadReminders = async () => {
    setLoading(true)
    try {
      const result = await getDueReminders()
      setContacts(result.contacts || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadUpcoming = async () => {
    setUpcomingLoading(true)
    try {
      const result = await getUpcomingReminders(10)
      setUpcoming(result.contacts || [])
    } catch (err) {
      // Don't surface this in the main error banner - the upcoming panel
      // failing to load shouldn't block the primary due-reminders view.
      console.error('Failed to load upcoming reminders:', err)
    } finally {
      setUpcomingLoading(false)
    }
  }

  const handleMarkContacted = async (contactId) => {
    try {
      await markContacted(contactId)
      setContacts(contacts.filter(c => c.id !== contactId))
      // A "mark contacted" reschedules the contact's next reminder further
      // out, so the upcoming panel's ordering/membership can change too.
      loadUpcoming()
    } catch (err) {
      setError(err.message)
    }
  }

  const formatFrequency = (freq) => {
    const map = {
      'every_3_days': 'Every 3 days',
      'weekly': 'Weekly',
      'every_2_weeks': 'Every 2 weeks',
      'monthly': 'Monthly',
    }
    return map[freq] || freq
  }

  const daysSince = (dateStr) => {
    if (!dateStr) return null
    const days = Math.floor((new Date() - new Date(dateStr)) / (1000 * 60 * 60 * 24))
    if (days === 0) return 'Today'
    if (days === 1) return '1 day ago'
    return `${days} days ago`
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 items-start">
      {/* Main content — unchanged: today's due-for-catch-up list */}
      <div className="flex-1 min-w-0 w-full space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
              Stay in Touch
            </h1>
            <p className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {contacts.length} contact{contacts.length !== 1 ? 's' : ''} due for a catch-up
            </p>
          </div>
          <button
            onClick={loadReminders}
            className="btn-secondary flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
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
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="card h-20 animate-pulse"
                style={{ backgroundColor: 'var(--color-bg-secondary)' }}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && contacts.length === 0 && (
          <div
            className="card p-12 text-center"
            style={{ backgroundColor: 'rgba(16, 185, 129, 0.05)' }}
          >
            <div
              className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
              style={{ backgroundColor: 'var(--color-success)' }}
            >
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="font-semibold text-lg mb-1" style={{ color: 'var(--color-text)' }}>
              All caught up!
            </p>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              No contacts due for a catch-up right now.
            </p>
            <Link to="/contacts" className="btn-primary mt-6 inline-block">
              View All Contacts
            </Link>
          </div>
        )}

        {/* Reminders list */}
        {!loading && contacts.length > 0 && (
          <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {contacts.map(contact => (
              <div key={contact.id} className="px-4 py-4 flex items-center justify-between">
                <Link
                  to={`/contacts/${contact.id}`}
                  className="flex items-center flex-1 min-w-0"
                >
                  {/* Avatar */}
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-semibold text-white mr-4 flex-shrink-0"
                    style={{ backgroundColor: getAvatarColor(contact.name) }}
                  >
                    {contact.name?.charAt(0).toUpperCase()}
                  </div>

                  <div className="min-w-0">
                    <h3 className="font-medium truncate" style={{ color: 'var(--color-text)' }}>
                      {contact.name}
                    </h3>
                    {contact.company && (
                      <p className="text-sm truncate" style={{ color: 'var(--color-text-secondary)' }}>
                        {contact.company}
                      </p>
                    )}
                    <div className="flex items-center space-x-2 mt-1">
                      <span
                        className="text-xs px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: 'var(--color-accent-gold)',
                          color: 'white'
                        }}
                      >
                        {formatFrequency(contact.reminder_frequency)}
                      </span>
                      {contact.last_contacted_at && (
                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                          Last contact: {daysSince(contact.last_contacted_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>

                <button
                  onClick={() => handleMarkContacted(contact.id)}
                  className="ml-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2"
                  style={{
                    backgroundColor: 'var(--color-success)',
                    color: 'white'
                  }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Done</span>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Tips */}
        {!loading && contacts.length > 0 && (
          <div
            className="card p-4 text-sm"
            style={{ backgroundColor: 'var(--color-bg-secondary)' }}
          >
            <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>
              💡 Quick tip
            </h4>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Click "Done" after you've reached out to a contact. This will reset their reminder timer
              and remove them from this list until the next reminder is due.
            </p>
          </div>
        )}
      </div>

      {/* Upcoming reminders panel — contacts whose reminder isn't due yet */}
      <div className="w-full lg:w-72 flex-shrink-0 space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide px-1" style={{ color: 'var(--color-text-muted)' }}>
          Upcoming
        </h2>

        {upcomingLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="card h-14 animate-pulse"
                style={{ backgroundColor: 'var(--color-bg-secondary)' }}
              />
            ))}
          </div>
        ) : upcoming.length === 0 ? (
          <div className="card p-4 text-sm text-center" style={{ color: 'var(--color-text-muted)' }}>
            No upcoming reminders scheduled.
          </div>
        ) : (
          <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {upcoming.map(contact => (
              <Link
                key={contact.id}
                to={`/contacts/${contact.id}`}
                className="flex items-center px-3 py-3 hover:bg-secondary transition-colors"
              >
                {/* Avatar */}
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold text-white mr-3 flex-shrink-0"
                  style={{ backgroundColor: getAvatarColor(contact.name) }}
                >
                  {contact.name?.charAt(0).toUpperCase()}
                </div>

                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm truncate" style={{ color: 'var(--color-text)' }}>
                    {contact.name}
                  </p>
                  <p className="text-xs truncate" style={{ color: 'var(--color-text-muted)' }}>
                    {formatUpcoming(contact.next_reminder_at)}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default RemindersPage