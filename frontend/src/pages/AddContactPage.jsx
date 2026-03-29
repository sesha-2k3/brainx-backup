// AddContactPage.jsx — Manual contact creation form

import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { confirmProposal, tokenStorage } from '../api/client'

function AddContactPage() {
  const navigate  = useNavigate()
  const location  = useLocation()

  // Populated when arriving from QuickCapturePanel's "Edit Details"
  const prefill          = location.state?.extracted   ?? {}
  const prefillProposalId = location.state?.proposalId ?? null

  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  // Seed every field from the AI extraction if present
  const [formData, setFormData] = useState({
    name:                prefill.name                ?? '',
    email:               prefill.email               ?? '',
    phone:               prefill.phone               ?? '',
    company:             prefill.company              ?? '',
    role:                prefill.role                 ?? '',
    category:            prefill.category             ?? '',
    context:             prefill.context              ?? '',
    notes:               '',
    interaction_summary: prefill.interaction_summary  ?? '',
    tasks:               prefill.tasks               ?? [],
  })

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.name.trim()) return

    setLoading(true)
    setError(null)

    try {
      if (prefillProposalId) {
        // Came from AI extraction — confirm the existing proposal so we don't
        // create a duplicate. The edited formData is the user's reviewed version.
        const result = await confirmProposal(prefillProposalId, {
          ...formData,
          tasks: formData.tasks ?? [],
        })
        navigate(`/contacts/${result.contact_id ?? result.contact?.id}`)
      } else {
        // Purely manual entry — create contact directly
        const token = tokenStorage.get()
        const response = await fetch('/brainx/api/contacts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(formData),
        })

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.detail || 'Failed to create contact')
        }

        const data = await response.json()
        navigate(`/contacts/${data.contact.id}`)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate('/contacts')}
          className="p-2 rounded-lg hover:bg-secondary transition-colors"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
          Add Contact
        </h1>
        {/* Badge shown when fields were pre-filled by AI */}
        {prefillProposalId && (
          <span className="ml-auto text-xs font-semibold px-2.5 py-1 rounded-full"
            style={{ backgroundColor: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>
            AI Extracted
          </span>
        )}
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

      {/* Form */}
      <form onSubmit={handleSubmit} className="card p-6 space-y-6">

        {/* Basic Info */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'var(--color-text-muted)' }}>
            Basic Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Name <span style={{ color: 'var(--color-error)' }}>*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                className="input"
                placeholder="John Smith"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                className="input"
                placeholder="john@example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Phone
              </label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                className="input"
                placeholder="+1 555 123 4567"
              />
            </div>
          </div>
        </div>

        {/* Professional Info */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'var(--color-text-muted)' }}>
            Professional
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Company
              </label>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => handleChange('company', e.target.value)}
                className="input"
                placeholder="Acme Corp"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Role
              </label>
              <input
                type="text"
                value={formData.role}
                onChange={(e) => handleChange('role', e.target.value)}
                className="input"
                placeholder="VP of Sales"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Category
              </label>
              <select
                value={formData.category}
                onChange={(e) => handleChange('category', e.target.value)}
                className="input"
              >
                <option value="">Select category...</option>
                <option value="investor">Investor</option>
                <option value="client">Client</option>
                <option value="partner">Partner</option>
                <option value="friend">Friend</option>
                <option value="family">Family</option>
                <option value="colleague">Colleague</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
        </div>

        {/* Additional Info */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'var(--color-text-muted)' }}>
            Additional Details
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Context (how you met)
              </label>
              <input
                type="text"
                value={formData.context}
                onChange={(e) => handleChange('context', e.target.value)}
                className="input"
                placeholder="Met at tech conference"
              />
            </div>
            {/* Interaction summary — pre-filled from AI, user can edit */}
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Interaction Notes
              </label>
              <textarea
                value={formData.interaction_summary}
                onChange={(e) => handleChange('interaction_summary', e.target.value)}
                rows={3}
                className="input resize-none"
                placeholder="What did you discuss?"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Notes
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                rows={3}
                className="input resize-none"
                placeholder="Additional notes about this contact..."
              />
            </div>
          </div>
        </div>

        {/* Tasks pre-filled from AI */}
        {formData.tasks?.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider mb-4"
              style={{ color: 'var(--color-text-muted)' }}>
              Tasks / Follow-ups ({formData.tasks.length})
            </h2>
            <div className="space-y-2">
              {formData.tasks.map((task, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-lg"
                  style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
                  <span className="flex-1 text-sm" style={{ color: 'var(--color-text)' }}>
                    {task.title}
                  </span>
                  {task.due_date && (
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {task.due_date}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <button
            type="button"
            onClick={() => navigate('/contacts')}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !formData.name.trim()}
            className="btn-primary"
          >
            {loading ? 'Saving...' : 'Save Contact'}
          </button>
        </div>
      </form>

      {!prefillProposalId && (
        <div className="card p-4 text-sm" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <h4 className="font-medium mb-1" style={{ color: 'var(--color-text)' }}>💡 Quick tip</h4>
          <p style={{ color: 'var(--color-text-secondary)' }}>
            You can also add contacts by pasting meeting notes, voice recordings, or business card
            images on the home page. BrainX will automatically extract contact information for you.
          </p>
        </div>
      )}
    </div>
  )
}

export default AddContactPage