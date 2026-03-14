// ExtractionPreview.jsx — Shows extracted data with inline editing before confirmation

import { useState } from 'react'

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
    <form onSubmit={handleSubmit} className="card p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
          Review Extracted Information
        </h3>
        <span 
          className="px-2 py-1 text-xs font-medium rounded-full"
          style={{ backgroundColor: 'var(--color-success)', color: 'white' }}
        >
          AI Extracted
        </span>
      </div>
      
      {/* Basic Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
            Name <span style={{ color: 'var(--color-error)' }}>*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className="input"
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
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
            Company
          </label>
          <input
            type="text"
            value={formData.company}
            onChange={(e) => handleChange('company', e.target.value)}
            className="input"
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
            <option value="">Select...</option>
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
          Context (how you met)
        </label>
        <input
          type="text"
          value={formData.context}
          onChange={(e) => handleChange('context', e.target.value)}
          className="input"
          placeholder="e.g., Met at tech conference"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
          Interaction Notes
        </label>
        <textarea
          value={formData.interaction_summary}
          onChange={(e) => handleChange('interaction_summary', e.target.value)}
          rows={2}
          className="input resize-none"
          placeholder="What did you discuss?"
        />
      </div>

      {/* Tasks Section */}
      <div className="pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
            Tasks / Follow-ups ({formData.tasks.length})
          </label>
          <button
            type="button"
            onClick={addTask}
            className="text-sm font-medium flex items-center space-x-1"
            style={{ color: 'var(--color-primary)' }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Add Task</span>
          </button>
        </div>
        
        {formData.tasks.length === 0 ? (
          <p className="text-sm py-4 text-center" style={{ color: 'var(--color-text-muted)' }}>
            No tasks extracted. Click "Add Task" to add one.
          </p>
        ) : (
          <div className="space-y-3">
            {formData.tasks.map((task, index) => (
              <div 
                key={index} 
                className="flex items-start space-x-2 p-3 rounded-lg"
                style={{ backgroundColor: 'var(--color-bg-secondary)' }}
              >
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={task.title}
                    onChange={(e) => handleTaskChange(index, 'title', e.target.value)}
                    placeholder="Task description"
                    className="input text-sm"
                  />
                  <input
                    type="text"
                    value={task.due_date || ''}
                    onChange={(e) => handleTaskChange(index, 'due_date', e.target.value)}
                    placeholder="Due date (e.g., tomorrow)"
                    className="input text-sm"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeTask(index)}
                  className="p-1.5 rounded hover:bg-secondary transition-colors"
                  style={{ color: 'var(--color-error)' }}
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

      {/* Actions */}
      <div className="flex justify-end space-x-3 pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <button
          type="button"
          onClick={onCancel}
          className="btn-secondary"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || !formData.name.trim()}
          className="btn-primary"
        >
          {submitting ? 'Saving...' : 'Save Contact'}
        </button>
      </div>
    </form>
  )
}

export default ExtractionPreview
