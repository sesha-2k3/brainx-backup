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
    loadTasks()
    loadContacts()
  }, [])

  const loadTasks = async () => {
    try {
      const result = await listTasks()
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

  const filteredTasks = showCompleted 
    ? tasks 
    : tasks.filter(t => t.status !== 'completed')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Tasks</h1>
        <label className="flex items-center space-x-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
            className="rounded border-gray-300"
          />
          <span>Show completed</span>
        </label>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
          <button onClick={() => setError(null)} className="float-right">&times;</button>
        </div>
      )}

      {/* Quick Add Task */}
      <form onSubmit={handleAddTask} className="bg-white rounded-lg shadow p-4">
        <div className="flex space-x-3">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Add a new task..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <input
            type="date"
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={!newTitle.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-blue-300"
          >
            Add
          </button>
        </div>
      </form>

      {/* Tasks List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : filteredTasks.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          {showCompleted ? 'No tasks yet.' : 'No pending tasks. You\'re all caught up!'}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow divide-y">
          {filteredTasks.map(task => (
            <div
              key={task.id}
              className={`px-6 py-4 ${
                task.status === 'completed' ? 'bg-gray-50 opacity-60' : ''
              } ${isOverdue(task) ? 'bg-red-50' : ''}`}
            >
              {editingTask === task.id ? (
                /* Edit Mode */
                <div className="space-y-3">
                  <input
                    type="text"
                    value={editForm.title}
                    onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    autoFocus
                  />
                  <div className="flex space-x-3">
                    <input
                      type="date"
                      value={editForm.due_date}
                      onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
                      className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <select
                      value={editForm.contact_id}
                      onChange={(e) => setEditForm({ ...editForm, contact_id: e.target.value })}
                      className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">No contact</option>
                      {contacts.map(c => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                    <div className="flex-1" />
                    <button
                      onClick={handleCancelEdit}
                      className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveEdit}
                      className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                /* View Mode */
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={() => handleComplete(task.id)}
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                        task.status === 'completed'
                          ? 'bg-green-500 border-green-500 text-white'
                          : 'border-gray-300 hover:border-green-500'
                      }`}
                    >
                      {task.status === 'completed' && (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                    <div 
                      className="cursor-pointer"
                      onClick={() => handleStartEdit(task)}
                    >
                      <p className={`font-medium ${task.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                        {task.title}
                      </p>
                      <div className="flex items-center space-x-2 text-sm text-gray-500">
                        {task.contact_name && (
                          <Link 
                            to={`/contacts/${task.contact_id}`} 
                            className="text-blue-600 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {task.contact_name}
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    {task.due_date && (
                      <span className={`text-sm ${isOverdue(task) ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
                        {formatDate(task.due_date)}
                      </span>
                    )}
                    <button
                      onClick={() => handleStartEdit(task)}
                      className="text-gray-400 hover:text-blue-600"
                      title="Edit"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDelete(task.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Delete"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
  )
}

export default TasksPage