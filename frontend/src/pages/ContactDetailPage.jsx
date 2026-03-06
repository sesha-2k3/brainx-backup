import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getContact, updateContact, deleteContact, createInteraction, updateInteraction, deleteInteraction } from '../api/client'

function ContactDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [contact, setContact] = useState(null)
  const [interactions, setInteractions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({})
  
  // Interaction state
  const [showAddInteraction, setShowAddInteraction] = useState(false)
  const [newInteraction, setNewInteraction] = useState({ summary: '', interaction_type: 'note' })
  const [editingInteraction, setEditingInteraction] = useState(null)
  const [editInteractionForm, setEditInteractionForm] = useState({ summary: '', interaction_type: '' })

  useEffect(() => {
    loadContact()
  }, [id])

  const loadContact = async () => {
    try {
      const result = await getContact(id)
      setContact(result.contact)
      setInteractions(result.interactions || [])
      setEditForm(result.contact)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      await updateContact(id, editForm)
      setContact(editForm)
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

  // Interaction handlers
  const handleAddInteraction = async (e) => {
    e.preventDefault()
    if (!newInteraction.summary.trim()) return
    
    try {
      await createInteraction({
        contact_id: id,
        summary: newInteraction.summary,
        interaction_type: newInteraction.interaction_type,
      })
      setNewInteraction({ summary: '', interaction_type: 'note' })
      setShowAddInteraction(false)
      loadContact()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleStartEditInteraction = (interaction) => {
    setEditingInteraction(interaction.id)
    setEditInteractionForm({
      summary: interaction.summary,
      interaction_type: interaction.interaction_type,
    })
  }

  const handleSaveInteraction = async () => {
    if (!editInteractionForm.summary.trim()) return
    
    try {
      await updateInteraction(editingInteraction, editInteractionForm)
      setEditingInteraction(null)
      loadContact()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteInteraction = async (interactionId) => {
    if (!confirm('Delete this interaction?')) return
    try {
      await deleteInteraction(interactionId)
      loadContact()
    } catch (err) {
      setError(err.message)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString()
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>
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
          {editing ? (
            <>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                Save
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setEditing(true)}
                className="px-4 py-2 text-sm font-medium text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50"
              >
                Edit
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium text-red-600 border border-red-600 rounded-lg hover:bg-red-50"
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
          <button onClick={() => setError(null)} className="float-right">&times;</button>
        </div>
      )}

      {/* Contact Details */}
      <div className="bg-white rounded-lg shadow p-6">
        {editing ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={editForm.email || ''}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input
                type="text"
                value={editForm.phone || ''}
                onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
              <input
                type="text"
                value={editForm.company || ''}
                onChange={(e) => setEditForm({ ...editForm, company: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <input
                type="text"
                value={editForm.role || ''}
                onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={editForm.category || ''}
                onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">Select...</option>
                <option value="investor">Investor</option>
                <option value="client">Client</option>
                <option value="partner">Partner</option>
                <option value="friend">Friend</option>
                <option value="family">Family</option>
                <option value="colleague">Colleague</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Context</label>
              <input
                type="text"
                value={editForm.context || ''}
                onChange={(e) => setEditForm({ ...editForm, context: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={editForm.notes || ''}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-6">
            {contact.email && (
              <div>
                <p className="text-sm text-gray-500">Email</p>
                <p className="text-gray-900">{contact.email}</p>
              </div>
            )}
            {contact.phone && (
              <div>
                <p className="text-sm text-gray-500">Phone</p>
                <p className="text-gray-900">{contact.phone}</p>
              </div>
            )}
            {contact.company && (
              <div>
                <p className="text-sm text-gray-500">Company</p>
                <p className="text-gray-900">{contact.company}</p>
              </div>
            )}
            {contact.role && (
              <div>
                <p className="text-sm text-gray-500">Role</p>
                <p className="text-gray-900">{contact.role}</p>
              </div>
            )}
            {contact.category && (
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="text-gray-900 capitalize">{contact.category}</p>
              </div>
            )}
            {contact.context && (
              <div>
                <p className="text-sm text-gray-500">Context</p>
                <p className="text-gray-900">{contact.context}</p>
              </div>
            )}
            {contact.notes && (
              <div className="col-span-2">
                <p className="text-sm text-gray-500">Notes</p>
                <p className="text-gray-900">{contact.notes}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Interactions */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Interactions</h2>
          <button
            onClick={() => setShowAddInteraction(!showAddInteraction)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            + Add Interaction
          </button>
        </div>

        {/* Add Interaction Form */}
        {showAddInteraction && (
          <div className="bg-white rounded-lg shadow p-4 mb-4">
            <form onSubmit={handleAddInteraction} className="space-y-3">
              <div className="flex space-x-3">
                <select
                  value={newInteraction.interaction_type}
                  onChange={(e) => setNewInteraction({ ...newInteraction, interaction_type: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="note">Note</option>
                  <option value="meeting">Meeting</option>
                  <option value="call">Call</option>
                  <option value="email">Email</option>
                </select>
                <input
                  type="text"
                  value={newInteraction.summary}
                  onChange={(e) => setNewInteraction({ ...newInteraction, summary: e.target.value })}
                  placeholder="What happened?"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddInteraction(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Add
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Interactions List */}
        {interactions.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No interactions recorded yet.</p>
        ) : (
          <div className="bg-white rounded-lg shadow divide-y">
            {interactions.map(interaction => (
              <div key={interaction.id} className="px-6 py-4">
                {editingInteraction === interaction.id ? (
                  /* Edit Mode */
                  <div className="space-y-3">
                    <div className="flex space-x-3">
                      <select
                        value={editInteractionForm.interaction_type}
                        onChange={(e) => setEditInteractionForm({ ...editInteractionForm, interaction_type: e.target.value })}
                        className="px-3 py-2 border border-gray-300 rounded-lg"
                      >
                        <option value="note">Note</option>
                        <option value="meeting">Meeting</option>
                        <option value="call">Call</option>
                        <option value="email">Email</option>
                      </select>
                      <input
                        type="text"
                        value={editInteractionForm.summary}
                        onChange={(e) => setEditInteractionForm({ ...editInteractionForm, summary: e.target.value })}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                        autoFocus
                      />
                    </div>
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => setEditingInteraction(null)}
                        className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveInteraction}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  /* View Mode */
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-blue-600 capitalize">{interaction.interaction_type}</p>
                      <p className="text-gray-900 mt-1">{interaction.summary}</p>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-sm text-gray-500">{formatDate(interaction.occurred_at)}</span>
                      <button
                        onClick={() => handleStartEditInteraction(interaction)}
                        className="text-gray-400 hover:text-blue-600"
                        title="Edit"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteInteraction(interaction.id)}
                        className="text-gray-400 hover:text-red-600"
                        title="Delete"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ContactDetailPage