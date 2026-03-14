// RecentContacts.jsx — Horizontal scrollable recent contacts

import { Link } from 'react-router-dom'

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

function RecentContacts({ contacts = [] }) {
  // Determine if contact was recently added (within last 24 hours)
  const isNew = (contact) => {
    if (!contact.created_at) return false
    const created = new Date(contact.created_at)
    const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
    return created > dayAgo
  }

  // Determine if contact was recently updated
  const isUpdated = (contact) => {
    if (!contact.updated_at || !contact.created_at) return false
    // Updated is different from created and within last 24 hours
    const updated = new Date(contact.updated_at)
    const created = new Date(contact.created_at)
    const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
    return updated > dayAgo && updated.getTime() !== created.getTime()
  }

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>
          Recent Profiles
        </h3>
        <Link 
          to="/contacts"
          className="text-sm font-medium"
          style={{ color: 'var(--color-primary)' }}
        >
          View All →
        </Link>
      </div>

      {contacts.length === 0 ? (
        <div 
          className="card p-8 text-center"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <p>No contacts yet. Add your first contact to get started!</p>
        </div>
      ) : (
        <div className="flex space-x-4 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
          {contacts.slice(0, 8).map(contact => (
            <Link
              key={contact.id}
              to={`/contacts/${contact.id}`}
              className="flex-shrink-0 w-36"
            >
              <div 
                className="card p-4 text-center hover:shadow-md transition-shadow"
              >
                {/* Avatar */}
                <div 
                  className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center text-lg font-semibold text-white"
                  style={{ backgroundColor: getAvatarColor(contact.name) }}
                >
                  {contact.name?.charAt(0).toUpperCase()}
                </div>

                {/* Badge */}
                {(isNew(contact) || isUpdated(contact)) && (
                  <span 
                    className={`
                      inline-block mb-2 text-xs font-medium px-2 py-0.5 rounded-full
                      ${isNew(contact) ? 'badge-new' : 'badge-updated'}
                    `}
                  >
                    {isNew(contact) ? 'NEW' : 'UPDATED'}
                  </span>
                )}

                {/* Name */}
                <p 
                  className="font-medium truncate"
                  style={{ color: 'var(--color-text)' }}
                >
                  {contact.name}
                </p>

                {/* Role & Company */}
                {(contact.role || contact.company) && (
                  <p 
                    className="text-xs truncate mt-1"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    {contact.role && contact.company 
                      ? `${contact.role} · ${contact.company}`
                      : contact.role || contact.company
                    }
                  </p>
                )}
              </div>
            </Link>
          ))}

          {/* Add contact card */}
          <Link
            to="/add-contact"
            className="flex-shrink-0 w-36"
          >
            <div 
              className="card p-4 text-center h-full flex flex-col items-center justify-center border-2 border-dashed hover:bg-secondary transition-colors cursor-pointer"
              style={{ borderColor: 'var(--color-border)', minHeight: '140px' }}
            >
              <div 
                className="w-12 h-12 rounded-full mb-3 flex items-center justify-center"
                style={{ backgroundColor: 'var(--color-bg-secondary)' }}
              >
                <svg 
                  className="w-6 h-6" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <p 
                className="text-sm font-medium"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Add Contact
              </p>
            </div>
          </Link>
        </div>
      )}
    </div>
  )
}

export default RecentContacts
