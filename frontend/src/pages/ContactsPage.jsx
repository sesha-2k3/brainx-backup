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

function ContactsPage() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [category, setCategory] = useState('all')

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
      // Update local state
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Contacts</h1>
        <span className="text-gray-500">{contacts.length} contacts</span>
      </div>

      {/* Category filter */}
      <div className="flex space-x-2 overflow-x-auto pb-2">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap ${
              category === cat
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      )}

      {/* Contact list */}
      {!loading && contacts.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No contacts yet. <Link to="/" className="text-blue-600 hover:underline">Add your first contact</Link>
        </div>
      )}

      {!loading && contacts.length > 0 && (
        <div className="bg-white rounded-lg shadow divide-y">
          {contacts.map(contact => (
            <div
              key={contact.id}
              className={`px-6 py-4 flex items-center justify-between ${
                isOverdue(contact) ? 'bg-orange-50' : ''
              }`}
            >
              <Link
                to={`/contacts/${contact.id}`}
                className="flex-1 hover:bg-gray-50 -my-4 -ml-6 py-4 pl-6"
              >
                <div className="flex items-center">
                  {isOverdue(contact) && (
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-3" title="Due for catch-up"></span>
                  )}
                  <div>
                    <h3 className="font-medium text-gray-900">{contact.name}</h3>
                    <p className="text-sm text-gray-500">
                      {[contact.role, contact.company].filter(Boolean).join(' at ') || 'No details'}
                    </p>
                  </div>
                </div>
              </Link>
              
              <div className="flex items-center space-x-3">
                {contact.category && (
                  <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                    {contact.category}
                  </span>
                )}
                
                {/* Reminder frequency dropdown */}
                <select
                  value={contact.reminder_frequency || 'none'}
                  onChange={(e) => handleFrequencyChange(contact.id, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="text-sm border border-gray-300 rounded-lg px-2 py-1 bg-white focus:ring-2 focus:ring-blue-500"
                  title="Stay in touch frequency"
                >
                  {FREQUENCIES.map(f => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
                
                <Link to={`/contacts/${contact.id}`}>
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ContactsPage