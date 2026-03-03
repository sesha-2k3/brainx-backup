// RemindersPage: Show contacts due for catch-up

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getDueReminders, markContacted } from '../api/client'

function RemindersPage() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadReminders()
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

  const handleMarkContacted = async (contactId) => {
    try {
      await markContacted(contactId)
      // Remove from list
      setContacts(contacts.filter(c => c.id !== contactId))
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Stay in Touch</h1>
        <button 
          onClick={loadReminders}
          className="text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      )}

      {!loading && contacts.length === 0 && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-6 py-8 rounded-lg text-center">
          <svg className="w-12 h-12 mx-auto mb-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <p className="font-medium">All caught up!</p>
          <p className="text-sm mt-1">No contacts due for a catch-up right now.</p>
        </div>
      )}

      {!loading && contacts.length > 0 && (
        <div className="space-y-4">
          <p className="text-gray-600">{contacts.length} contact(s) due for a catch-up</p>
          
          <div className="bg-white rounded-lg shadow divide-y">
            {contacts.map(contact => (
              <div key={contact.id} className="px-6 py-4 flex items-center justify-between">
                <div className="flex-1">
                  <Link 
                    to={`/contacts/${contact.id}`}
                    className="font-medium text-gray-900 hover:text-blue-600"
                  >
                    {contact.name}
                  </Link>
                  {contact.company && (
                    <p className="text-sm text-gray-500">{contact.company}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {formatFrequency(contact.reminder_frequency)}
                    {contact.last_contacted_at && ` · Last contact: ${daysSince(contact.last_contacted_at)}`}
                  </p>
                </div>
                
                <button
                  onClick={() => handleMarkContacted(contact.id)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                >
                  Mark Contacted
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default RemindersPage