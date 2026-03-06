// ExtractionPreview: Shows extracted data with inline editing before confirmation

import { useState, useEffect } from 'react'

const CATEGORIES = ['investor', 'client', 'partner', 'friend', 'family', 'colleague', 'other']

function ExtractionPreview({ data, proposalId, onConfirm, onCancel }) {
  
  // undefined check
  if (!data) {
    return null
  }

  const [formData, setFormData] = useState({
    name: data.name || '',
    email: data.email || '',
    phone: data.phone || '',
    company: data.company || '',
    role: data.role || '',
    category: data.category || '',
    context: data.context || '',
    interaction_summary: data.interaction_summary || '',
    tasks: data.tasks || [],
  })
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleTaskChange = (index, field, value) => {
    const newTasks = [...formData.tasks]
    newTasks[index] = { ...newTasks[index], [field]: value }
    setFormData(prev => ({ ...prev, tasks: newTasks }))
  }

  const addTask = () => {
    setFormData(prev => ({
      ...prev,
      tasks: [...prev.tasks, { title: '', due_date: '' }]
    }))
  }

  const removeTask = (index) => {
    setFormData(prev => ({
      ...prev,
      tasks: prev.tasks.filter((_, i) => i !== index)
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      // Filter out empty tasks
      const tasksToSubmit = formData.tasks.filter(t => t.title && t.title.trim())
      await onConfirm({ ...formData, tasks: tasksToSubmit })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
      <h3 className="text-lg font-medium text-gray-900">Review Extracted Information</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input
            type="text"
            value={formData.phone}
            onChange={(e) => handleChange('phone', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
          <input
            type="text"
            value={formData.company}
            onChange={(e) => handleChange('company', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <input
            type="text"
            value={formData.role}
            onChange={(e) => handleChange('role', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select
            value={formData.category}
            onChange={(e) => handleChange('category', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Context (how you met)</label>
        <input
          type="text"
          value={formData.context}
          onChange={(e) => handleChange('context', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          placeholder="e.g., Met at tech conference"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Interaction Notes</label>
        <textarea
          value={formData.interaction_summary}
          onChange={(e) => handleChange('interaction_summary', e.target.value)}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          placeholder="What did you discuss?"
        />
      </div>

      {/* Tasks Section */}
      <div className="border-t pt-4">
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-gray-700">
            Tasks / Follow-ups ({formData.tasks.length})
          </label>
          <button
            type="button"
            onClick={addTask}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            + Add Task
          </button>
        </div>
        
        {formData.tasks.length === 0 ? (
          <p className="text-sm text-gray-500">No tasks extracted. Click "Add Task" to add one.</p>
        ) : (
          <div className="space-y-3">
            {formData.tasks.map((task, index) => (
              <div key={index} className="flex items-start space-x-2 bg-gray-50 p-3 rounded-lg">
                <div className="flex-1 grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={task.title}
                    onChange={(e) => handleTaskChange(index, 'title', e.target.value)}
                    placeholder="Task description"
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <input
                    type="text"
                    value={task.due_date || ''}
                    onChange={(e) => handleTaskChange(index, 'due_date', e.target.value)}
                    placeholder="Due date (e.g., tomorrow)"
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeTask(index)}
                  className="text-red-500 hover:text-red-700 p-1"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex justify-end space-x-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
        >
          {submitting ? 'Saving...' : 'Save Contact'}
        </button>
      </div>
    </form>
  )
}

export default ExtractionPreview