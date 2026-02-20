// ContactDetailPage: View and edit a single contact with interactions

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getContact, updateContact, deleteContact } from '../api/client'

function ContactDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [contact, setContact] = useState(null)
  const [interactions, setInteractions] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editData, setEditData] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    loadContact()
  }, [id])

  const loadContact = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getContact(id)
      setContact(result.contact)
      setInteractions(result.interactions || [])
      setEditData(result.contact)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      const result = await updateContact(id, editData)
      setContact(result.contact)
      setEditing(false)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this contact?')) return
    try {
      await deleteContact(id)
      navigate('/contacts')
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    )
  }

  if (!contact) {
    return <div className="text-center py-12 text-gray-500">Contact not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/contacts" className="text-gray-500 hover:text-gray-700">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <h1 className="text-2xl font-semibold text-gray-900">{contact.name}</h1>
        </div>
        <div className="flex space-x-2">
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="px-4 py-2 text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
            >
              Edit
            </button>
          )}
          <button
            onClick={handleDelete}
            className="px-4 py-2 text-red-600 bg-red-50 rounded-lg hover:bg-red-100"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Contact details */}
      <div className="bg-white rounded-lg shadow p-6">
        {editing ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={editData.name || ''}
                  onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={editData.category || ''}
                  onChange={(e) => setEditData({ ...editData, category: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">Select...</option>
                  {['investor', 'client', 'partner', 'friend', 'family', 'colleague', 'other'].map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={editData.email || ''}
                  onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="tel"
                  value={editData.phone || ''}
                  onChange={(e) => setEditData({ ...editData, phone: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                <input
                  type="text"
                  value={editData.company || ''}
                  onChange={(e) => setEditData({ ...editData, company: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <input
                  type="text"
                  value={editData.role || ''}
                  onChange={(e) => setEditData({ ...editData, role: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={editData.notes || ''}
                onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => { setEditing(false); setEditData(contact) }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-4">
            {contact.email && (
              <div>
                <dt className="text-sm text-gray-500">Email</dt>
                <dd className="text-gray-900">{contact.email}</dd>
              </div>
            )}
            {contact.phone && (
              <div>
                <dt className="text-sm text-gray-500">Phone</dt>
                <dd className="text-gray-900">{contact.phone}</dd>
              </div>
            )}
            {contact.company && (
              <div>
                <dt className="text-sm text-gray-500">Company</dt>
                <dd className="text-gray-900">{contact.company}</dd>
              </div>
            )}
            {contact.role && (
              <div>
                <dt className="text-sm text-gray-500">Role</dt>
                <dd className="text-gray-900">{contact.role}</dd>
              </div>
            )}
            {contact.category && (
              <div>
                <dt className="text-sm text-gray-500">Category</dt>
                <dd className="text-gray-900 capitalize">{contact.category}</dd>
              </div>
            )}
            {contact.context && (
              <div className="col-span-2">
                <dt className="text-sm text-gray-500">Context</dt>
                <dd className="text-gray-900">{contact.context}</dd>
              </div>
            )}
            {contact.notes && (
              <div className="col-span-2">
                <dt className="text-sm text-gray-500">Notes</dt>
                <dd className="text-gray-900 whitespace-pre-wrap">{contact.notes}</dd>
              </div>
            )}
          </dl>
        )}
      </div>

      {/* Interactions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Interactions</h2>
        {interactions.length === 0 ? (
          <p className="text-gray-500">No interactions recorded yet.</p>
        ) : (
          <div className="space-y-3">
            {interactions.map(interaction => (
              <div key={interaction.id} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-500 capitalize">
                    {interaction.interaction_type}
                  </span>
                  <span className="text-sm text-gray-400">
                    {new Date(interaction.occurred_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-gray-700">{interaction.summary}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ContactDetailPage
