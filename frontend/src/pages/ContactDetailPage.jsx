// ContactDetailPage.jsx — Contact detail view with interactions

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getContact, updateContact, deleteContact, createInteraction, updateInteraction, deleteInteraction } from '../api/client'

// Avatar colors
const avatarColors = {
  A: '#C43B3B', B: '#3B5DC9', C: '#2D8F4E', D: '#D4A03B',
  E: '#8B5CF6', F: '#EC4899', G: '#14B8A6', H: '#F97316',
  I: '#06B6D4', J: '#84CC16', K: '#EF4444', L: '#3B82F6',
  M: '#10B981', N: '#F59E0B', O: '#6366F1', P: '#EC4899',
}

const getAvatarColor = (name) => {
  const firstLetter = (name || 'A').charAt(0).toUpperCase()
  return avatarColors[firstLetter] || '#6B7280'
}

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
  // Tracks which interaction's raw transcript is currently expanded (only
  // one at a time, id of the interaction or null)
  const [expandedTranscript, setExpandedTranscript] = useState(null)

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

  const toggleTranscript = (interactionId) => {
    setExpandedTranscript(current => current === interactionId ? null : interactionId)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="card h-48 animate-pulse" style={{ backgroundColor: 'var(--color-bg-secondary)' }} />
        <div className="card h-64 animate-pulse" style={{ backgroundColor: 'var(--color-bg-secondary)' }} />
      </div>
    )
  }

  if (!contact) {
    return (
      <div className="card p-12 text-center">
        <svg
          className="w-16 h-16 mx-auto mb-4 opacity-50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>Contact not found</p>
        <Link to="/contacts" className="btn-primary">Back to Contacts</Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/contacts"
            className="p-2 rounded-lg hover:bg-secondary transition-colors"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex items-center space-x-3">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-semibold text-white"
              style={{ backgroundColor: getAvatarColor(contact.name) }}
            >
              {contact.name?.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
                {contact.name}
              </h1>
              {(contact.role || contact.company) && (
                <p style={{ color: 'var(--color-text-secondary)' }}>
                  {contact.role && contact.company
                    ? `${contact.role} at ${contact.company}`
                    : contact.role || contact.company
                  }
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="flex space-x-2">
          {editing ? (
            <>
              <button
                onClick={() => setEditing(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="btn-primary"
              >
                Save
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setEditing(true)}
                className="btn-secondary"
              >
                Edit
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium rounded-lg border transition-colors"
                style={{
                  color: 'var(--color-error)',
                  borderColor: 'var(--color-error)'
                }}
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          className="px-4 py-3 rounded-lg flex items-center justify-between"
          style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-error)' }}
        >
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-lg">&times;</button>
        </div>
      )}

      {/* Contact Details */}
      <div className="card p-6">
        {editing ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Name
              </label>
              <input
                type="text"
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Email
              </label>
              <input
                type="email"
                value={editForm.email || ''}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Phone
              </label>
              <input
                type="text"
                value={editForm.phone || ''}
                onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Company
              </label>
              <input
                type="text"
                value={editForm.company || ''}
                onChange={(e) => setEditForm({ ...editForm, company: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Role
              </label>
              <input
                type="text"
                value={editForm.role || ''}
                onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Category
              </label>
              <select
                value={editForm.category || ''}
                onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                className="input"
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
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Context
              </label>
              <input
                type="text"
                value={editForm.context || ''}
                onChange={(e) => setEditForm({ ...editForm, context: e.target.value })}
                className="input"
                placeholder="How did you meet?"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Notes
              </label>
              <textarea
                value={editForm.notes || ''}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                rows={3}
                className="input resize-none"
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {contact.email && (
              <div>
                <p className="text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Email</p>
                <a
                  href={`mailto:${contact.email}`}
                  className="font-medium hover:underline"
                  style={{ color: 'var(--color-primary)' }}
                >
                  {contact.email}
                </a>
              </div>
            )}
            {contact.phone && (
              <div>
                <p className="text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Phone</p>
                <a
                  href={`tel:${contact.phone}`}
                  className="font-medium"
                  style={{ color: 'var(--color-text)' }}
                >
                  {contact.phone}
                </a>
              </div>
            )}
            {contact.category && (
              <div>
                <p className="text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Category</p>
                <span
                  className="inline-block px-2 py-1 text-sm font-medium rounded capitalize"
                  style={{
                    backgroundColor: 'var(--color-primary-light)',
                    color: 'var(--color-primary)'
                  }}
                >
                  {contact.category}
                </span>
              </div>
            )}
            {contact.context && (
              <div>
                <p className="text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Context</p>
                <p style={{ color: 'var(--color-text)' }}>{contact.context}</p>
              </div>
            )}
            {contact.notes && (
              <div className="md:col-span-2">
                <p className="text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Notes</p>
                <p style={{ color: 'var(--color-text)' }}>{contact.notes}</p>
              </div>
            )}
            {!contact.email && !contact.phone && !contact.category && !contact.context && !contact.notes && (
              <div className="md:col-span-2 text-center py-4" style={{ color: 'var(--color-text-muted)' }}>
                No additional details. Click "Edit" to add more information.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Interactions */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
            Interactions
          </h2>
          <button
            onClick={() => setShowAddInteraction(!showAddInteraction)}
            className="text-sm font-medium flex items-center space-x-1"
            style={{ color: 'var(--color-primary)' }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Add Interaction</span>
          </button>
        </div>

        {/* Add Interaction Form */}
        {showAddInteraction && (
          <div className="card p-4 mb-4">
            <form onSubmit={handleAddInteraction} className="space-y-3">
              <div className="flex space-x-3">
                <select
                  value={newInteraction.interaction_type}
                  onChange={(e) => setNewInteraction({ ...newInteraction, interaction_type: e.target.value })}
                  className="input w-auto"
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
                  className="input flex-1"
                  autoFocus
                />
              </div>
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddInteraction(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                >
                  Add
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Interactions List */}
        {interactions.length === 0 ? (
          <div
            className="card p-8 text-center"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <svg
              className="w-12 h-12 mx-auto mb-3 opacity-50"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p>No interactions recorded yet.</p>
            <button
              onClick={() => setShowAddInteraction(true)}
              className="btn-primary mt-4"
            >
              Add First Interaction
            </button>
          </div>
        ) : (
          <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {interactions.map(interaction => (
              <div key={interaction.id} className="px-4 py-4">
                {editingInteraction === interaction.id ? (
                  /* Edit Mode */
                  <div className="space-y-3">
                    <div className="flex space-x-3">
                      <select
                        value={editInteractionForm.interaction_type}
                        onChange={(e) => setEditInteractionForm({ ...editInteractionForm, interaction_type: e.target.value })}
                        className="input w-auto"
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
                        className="input flex-1"
                        autoFocus
                      />
                    </div>
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => setEditingInteraction(null)}
                        className="btn-secondary text-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveInteraction}
                        className="btn-primary text-sm"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  /* View Mode */
                  <>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <span
                          className="text-xs font-medium uppercase tracking-wider"
                          style={{ color: 'var(--color-primary)' }}
                        >
                          {interaction.interaction_type}
                        </span>
                        <p className="mt-1" style={{ color: 'var(--color-text)' }}>
                          {interaction.summary}
                        </p>
                        {/* Only shown when this interaction actually has a
                            stored raw transcript (AI-extracted interactions
                            going forward - not manually-added notes, and not
                            interactions created before this feature existed) */}
                        {interaction.raw_transcript && (
                          <button
                            onClick={() => toggleTranscript(interaction.id)}
                            className="mt-2 text-xs font-medium flex items-center space-x-1"
                            style={{ color: 'var(--color-text-muted)' }}
                          >
                            <svg
                              className="w-3.5 h-3.5 transition-transform"
                              style={{ transform: expandedTranscript === interaction.id ? 'rotate(90deg)' : 'none' }}
                              fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                            <span>
                              {expandedTranscript === interaction.id ? 'Hide transcription' : 'View transcription'}
                            </span>
                          </button>
                        )}
                      </div>
                      <div className="flex items-center space-x-3 ml-4">
                        <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                          {formatDate(interaction.occurred_at)}
                        </span>
                        <button
                          onClick={() => handleStartEditInteraction(interaction)}
                          className="p-1 rounded hover:bg-secondary transition-colors"
                          style={{ color: 'var(--color-text-muted)' }}
                          title="Edit"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDeleteInteraction(interaction.id)}
                          className="p-1 rounded hover:bg-secondary transition-colors"
                          style={{ color: 'var(--color-text-muted)' }}
                          title="Delete"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* Expanded raw transcript panel */}
                    {expandedTranscript === interaction.id && interaction.raw_transcript && (
                      <div
                        className="mt-3 p-3 rounded-lg text-sm whitespace-pre-wrap"
                        style={{ backgroundColor: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)' }}
                      >
                        {interaction.raw_transcript}
                      </div>
                    )}
                  </>
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