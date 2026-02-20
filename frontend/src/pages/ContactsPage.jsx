// ContactsPage: List all contacts with filtering

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listContacts } from '../api/client'

const CATEGORIES = ['all', 'investor', 'client', 'partner', 'friend', 'family', 'colleague', 'other']

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
            <Link
              key={contact.id}
              to={`/contacts/${contact.id}`}
              className="block px-6 py-4 hover:bg-gray-50"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{contact.name}</h3>
                  <p className="text-sm text-gray-500">
                    {[contact.role, contact.company].filter(Boolean).join(' at ') || 'No details'}
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  {contact.category && (
                    <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                      {contact.category}
                    </span>
                  )}
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default ContactsPage
