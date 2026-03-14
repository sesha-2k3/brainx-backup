// DueReminders.jsx — Contacts due for catch-up

import { Link } from 'react-router-dom'
import { markContacted } from '../../api/client'

function DueReminders({ contacts = [], onMarkContacted }) {
  const handleMarkContacted = async (contactId) => {
    try {
      await markContacted(contactId)
      onMarkContacted?.(contactId)
    } catch (err) {
      console.error('Failed to mark contacted:', err)
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

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>
          Stay in Touch
        </h3>
        <Link 
          to="/reminders"
          className="text-sm font-medium"
          style={{ color: 'var(--color-primary)' }}
        >
          View All →
        </Link>
      </div>

      {contacts.length === 0 ? (
        <div 
          className="text-center py-6"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-sm">All caught up!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {contacts.slice(0, 4).map(contact => (
            <div 
              key={contact.id}
              className="flex items-center justify-between p-3 rounded-lg hover:bg-secondary transition-colors"
            >
              <Link 
                to={`/contacts/${contact.id}`}
                className="flex items-center flex-1 min-w-0"
              >
                {/* Avatar */}
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium mr-3 flex-shrink-0"
                  style={{ 
                    backgroundColor: 'var(--color-accent-gold)',
                    color: 'white'
                  }}
                >
                  {contact.name?.charAt(0).toUpperCase()}
                </div>
                
                <div className="min-w-0">
                  <p 
                    className="font-medium truncate"
                    style={{ color: 'var(--color-text)' }}
                  >
                    {contact.name}
                  </p>
                  <p 
                    className="text-xs truncate"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    {formatFrequency(contact.reminder_frequency)}
                  </p>
                </div>
              </Link>

              <button
                onClick={(e) => {
                  e.preventDefault()
                  handleMarkContacted(contact.id)
                }}
                className="ml-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
                style={{ 
                  backgroundColor: 'var(--color-accent-green)',
                  color: 'white'
                }}
              >
                Done
              </button>
            </div>
          ))}
        </div>
      )}

      {contacts.length > 4 && (
        <Link 
          to="/reminders"
          className="block mt-3 text-center text-sm py-2"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          +{contacts.length - 4} more
        </Link>
      )}
    </div>
  )
}

export default DueReminders
