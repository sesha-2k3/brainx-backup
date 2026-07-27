// TasksPage.jsx — Task list with create, edit, complete, delete

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listTasks, createTask, updateTask, completeTask, deleteTask, listContacts } from '../api/client'

function TasksPage() {
  const [tasks, setTasks] = useState([])
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCompleted, setShowCompleted] = useState(false)

  // New task form
  const [newTitle, setNewTitle] = useState('')
  const [newDueDate, setNewDueDate] = useState('')

  // Edit state
  const [editingTask, setEditingTask] = useState(null)
  const [editForm, setEditForm] = useState({ title: '', due_date: '', contact_id: '' })

  useEffect(() => {
    loadContacts()
  }, [])

  // Refetch whenever the toggle changes - previously tasks were fetched
  // once on mount with no params, so completed tasks never made it into
  // state at all regardless of the toggle.
  useEffect(() => {
    loadTasks()
  }, [showCompleted])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const result = await listTasks({ include_completed: showCompleted })
      setTasks(result.tasks || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadContacts = async () => {
    try {
      const result = await listContacts()
      setContacts(result.contacts || [])
    } catch (err) {
      console.error('Failed to load contacts:', err)
    }
  }

  const handleAddTask = async (e) => {
    e.preventDefault()
    if (!newTitle.trim()) return

    try {
      await createTask({
        title: newTitle,
        due_date: newDueDate || null,
      })
      setNewTitle('')
      setNewDueDate('')
      loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleStartEdit = (task) => {
    setEditingTask(task.id)
    setEditForm({
      title: task.title,
      due_date: task.due_date ? task.due_date.split('T')[0] : '',
      contact_id: task.contact_id || '',
    })
  }

  const handleCancelEdit = () => {
    setEditingTask(null)
    setEditForm({ title: '', due_date: '', contact_id: '' })
  }

  const handleSaveEdit = async () => {
    if (!editForm.title.trim()) return

    try {
      await updateTask(editingTask, {
        title: editForm.title,
        due_date: editForm.due_date || null,
        contact_id: editForm.contact_id || null,
      })
      setEditingTask(null)
      loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleComplete = async (taskId) => {
    try {
      await completeTask(taskId)
      loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async (taskId) => {
    if (!confirm('Delete this task?')) return
    try {
      await deleteTask(taskId)
      loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  const isOverdue = (task) => {
    if (!task.due_date || task.status === 'completed') return false
    return new Date(task.due_date) < new Date()
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    const today = new Date()
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)

    if (date.toDateString() === today.toDateString()) return 'Today'
    if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const formatCompletedDate = (dateStr) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === today.toDateString()) {
      return `Today, ${date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`
    }
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  // Backend already orders pending tasks by due date and completed tasks by
  // completed_at descending (latest finished first) - split here just for
  // separate section rendering, order is preserved from the API response.
  const pendingTasks = tasks.filter(t => t.status !== 'completed')
  const completedTasks = tasks.filter(t => t.status === 'completed')

  const pendingCount = pendingTasks.length
  const overdueCount = pendingTasks.filter(t => isOverdue(t)).length

  const renderTaskRow = (task) => (
    <div
      key={task.id}
      className={`px-4 py-4 ${task.status === 'completed' ? 'opacity-60' : ''}`}
      style={isOverdue(task) ? { backgroundColor: 'rgba(239, 68, 68, 0.05)' } : {}}
    >
      {editingTask === task.id ? (
        /* Edit Mode */
        <div className="space-y-3">
          <input
            type="text"
            value={editForm.title}
            onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
            className="input"
            autoFocus
          />
          <div className="flex flex-wrap gap-3">
            <input
              type="date"
              value={editForm.due_date}
              onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
              className="input w-auto"
            />
            <select
              value={editForm.contact_id}
              onChange={(e) => setEditForm({ ...editForm, contact_id: e.target.value })}
              className="input w-auto"
            >
              <option value="">No contact</option>
              {contacts.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <div className="flex-1" />
            <button onClick={handleCancelEdit} className="btn-secondary">
              Cancel
            </button>
            <button onClick={handleSaveEdit} className="btn-primary">
              Save
            </button>
          </div>
        </div>
      ) : (
        /* View Mode */
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1 min-w-0">
            {/* Checkbox */}
            <button
              onClick={() => handleComplete(task.id)}
              className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors"
              style={task.status === 'completed'
                ? { backgroundColor: 'var(--color-success)', borderColor: 'var(--color-success)' }
                : { borderColor: 'var(--color-border)' }
              }
              disabled={task.status === 'completed'}
            >
              {task.status === 'completed' && (
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>

            {/* Task info */}
            <div
              className="cursor-pointer flex-1 min-w-0"
              onClick={() => handleStartEdit(task)}
            >
              <p
                className={`font-medium truncate ${task.status === 'completed' ? 'line-through' : ''}`}
                style={{ color: task.status === 'completed' ? 'var(--color-text-muted)' : 'var(--color-text)' }}
              >
                {task.title}
              </p>
              {task.contact_name && (
                <Link
                  to={`/contacts/${task.contact_id}`}
                  className="text-sm hover:underline"
                  style={{ color: 'var(--color-primary)' }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {task.contact_name}
                </Link>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3 ml-4">
            {/* Due date or completed date */}
            {task.status === 'completed' ? (
              task.completed_at && (
                <span className="text-sm whitespace-nowrap" style={{ color: 'var(--color-text-muted)' }}>
                  Completed {formatCompletedDate(task.completed_at)}
                </span>
              )
            ) : (
              task.due_date && (
                <span
                  className="text-sm font-medium whitespace-nowrap"
                  style={{ color: isOverdue(task) ? 'var(--color-error)' : 'var(--color-text-secondary)' }}
                >
                  {formatDate(task.due_date)}
                </span>
              )
            )}

            {/* Edit button */}
            <button
              onClick={() => handleStartEdit(task)}
              className="p-1.5 rounded hover:bg-secondary transition-colors"
              style={{ color: 'var(--color-text-muted)' }}
              title="Edit"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>

            {/* Delete button */}
            <button
              onClick={() => handleDelete(task.id)}
              className="p-1.5 rounded hover:bg-secondary transition-colors"
              style={{ color: 'var(--color-text-muted)' }}
              title="Delete"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            Tasks
          </h1>
          <div className="flex items-center space-x-4 mt-1">
            <span style={{ color: 'var(--color-text-secondary)' }}>
              {pendingCount} pending
            </span>
            {overdueCount > 0 && (
              <span style={{ color: 'var(--color-error)' }}>
                {overdueCount} overdue
              </span>
            )}
          </div>
        </div>

        {/* Toggle slider for showing completed tasks */}
        <label className="flex items-center space-x-3 text-sm cursor-pointer select-none">
          <span style={{ color: 'var(--color-text-secondary)' }}>Show completed</span>
          <span
            role="switch"
            aria-checked={showCompleted}
            onClick={() => setShowCompleted(v => !v)}
            className="relative inline-flex h-6 w-11 flex-shrink-0 rounded-full transition-colors duration-200"
            style={{
              backgroundColor: showCompleted ? 'var(--color-primary)' : 'var(--color-border)',
            }}
          >
            <span
              className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform duration-200 mt-0.5"
              style={{
                transform: showCompleted ? 'translateX(22px)' : 'translateX(2px)',
              }}
            />
          </span>
        </label>
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

      {/* Quick Add Task */}
      <form onSubmit={handleAddTask} className="card p-4">
        <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Add a new task..."
            className="input flex-1"
          />
          <input
            type="date"
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
            className="input sm:w-auto"
          />
          <button type="submit" disabled={!newTitle.trim()} className="btn-primary">
            Add Task
          </button>
        </div>
      </form>

      {/* Pending Tasks List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="card h-16 animate-pulse"
              style={{ backgroundColor: 'var(--color-bg-secondary)' }}
            />
          ))}
        </div>
      ) : pendingTasks.length === 0 && (!showCompleted || completedTasks.length === 0) ? (
        <div className="card p-12 text-center">
          <svg
            className="w-16 h-16 mx-auto mb-4 opacity-50"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          <p className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>
            All caught up!
          </p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            No pending tasks. Great job!
          </p>
        </div>
      ) : (
        <>
          {pendingTasks.length > 0 && (
            <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
              {pendingTasks.map(renderTaskRow)}
            </div>
          )}

          {showCompleted && completedTasks.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
                Completed ({completedTasks.length})
              </h2>
              <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
                {completedTasks.map(renderTaskRow)}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default TasksPage
