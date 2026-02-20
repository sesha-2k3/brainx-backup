// ExtractionPreview: Shows extracted data with inline editing before confirmation

import { useState, useEffect } from 'react'

const CATEGORIES = ['investor', 'client', 'partner', 'friend', 'family', 'colleague', 'other']

function ExtractionPreview({ proposal, onConfirm, onCancel, loading }) {
  const [data, setData] = useState({})

  useEffect(() => {
    if (proposal?.extracted_data) {
      setData(proposal.extracted_data)
    }
  }, [proposal])

  const handleChange = (field, value) => {
    setData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onConfirm(data)
  }

  const isDuplicate = proposal?.duplicate_contact != null

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          {isDuplicate ? 'Update Existing Contact' : 'New Contact'}
        </h2>
        {proposal?.confidence_score && (
          <span className="text-sm text-gray-500">
            Confidence: {Math.round(proposal.confidence_score * 100)}%
          </span>
        )}
      </div>

      {isDuplicate && (
        <div className="mb-4 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">
          Found existing contact: <strong>{proposal.duplicate_contact.name}</strong>. 
          New data will be merged.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            value={data.name || ''}
            onChange={(e) => handleChange('name', e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Email and Phone - side by side */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={data.email || ''}
              onChange={(e) => handleChange('email', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input
              type="tel"
              value={data.phone || ''}
              onChange={(e) => handleChange('phone', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Company and Role - side by side */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
            <input
              type="text"
              value={data.company || ''}
              onChange={(e) => handleChange('company', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <input
              type="text"
              value={data.role || ''}
              onChange={(e) => handleChange('role', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select
            value={data.category || ''}
            onChange={(e) => handleChange('category', e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select category...</option>
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Context */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Context (how you met)</label>
          <input
            type="text"
            value={data.context || ''}
            onChange={(e) => handleChange('context', e.target.value)}
            placeholder="E.g., Met at TechCrunch Disrupt 2024"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Interaction summary */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            value={data.interaction_summary || ''}
            onChange={(e) => handleChange('interaction_summary', e.target.value)}
            rows={3}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
        </div>

        {/* Follow-up */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Follow-up task</label>
            <input
              type="text"
              value={data.follow_up || ''}
              onChange={(e) => handleChange('follow_up', e.target.value)}
              placeholder="E.g., Send proposal"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Due date</label>
            <input
              type="date"
              value={data.follow_up_date || ''}
              onChange={(e) => handleChange('follow_up_date', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !data.name}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : 'Save Contact'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ExtractionPreview
