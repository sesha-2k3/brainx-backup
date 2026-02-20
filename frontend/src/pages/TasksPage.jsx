// TasksPage: List and manage tasks/follow-ups

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listTasks, completeTask, deleteTask, createTask } from '../api/client'

function TasksPage() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCompleted, setShowCompleted] = useState(false)
  const [newTask, setNewTask] = useState('')
  const [newTaskDate, setNewTaskDate] = useState('')

  useEffect(() => {
    loadTasks()
  }, [showCompleted])

  const loadTasks = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await listTasks({ include_completed: showCompleted })
      setTasks(result.tasks || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = async (id) => {
    try {
      await completeTask(id)
      setTasks(tasks.map(t => t.id === id ? { ...t, status: 'completed' } : t))
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteTask(id)
      setTasks(tasks.filter(t => t.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  const handleAddTask = async (e) => {
    e.preventDefault()
    if (!newTask.trim()) return
    
    try {
      const result = await createTask({
        title: newTask,
        due_date: newTaskDate || null,
      })
      setTasks([result.task, ...tasks])
      setNewTask('')
      setNewTaskDate('')
    } catch (err) {
      setError(err.message)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const taskDate = new Date(date)
    taskDate.setHours(0, 0, 0, 0)
    
    const diffDays = Math.ceil((taskDate - today) / (1000 * 60 * 60 * 24))
    
    if (diffDays < 0) return { text: 'Overdue', className: 'text-red-600' }
    if (diffDays === 0) return { text: 'Today', className: 'text-orange-600' }
    if (diffDays === 1) return { text: 'Tomorrow', className: 'text-yellow-600' }
    if (diffDays <= 7) return { text: date.toLocaleDateString('en-US', { weekday: 'short' }), className: 'text-gray-600' }
    return { text: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), className: 'text-gray-600' }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Tasks</h1>
        <label className="flex items-center space-x-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
            className="rounded"
          />
          <span>Show completed</span>
        </label>
      </div>

      {/* Quick add task */}
      <form onSubmit={handleAddTask} className="bg-white rounded-lg shadow p-4">
        <div className="flex space-x-3">
          <input
            type="text"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            placeholder="Add a new task..."
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
          />
          <input
            type="date"
            value={newTaskDate}
            onChange={(e) => setNewTaskDate(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2"
          />
          <button
            type="submit"
            disabled={!newTask.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </form>

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

      {/* Task list */}
      {!loading && tasks.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No tasks yet. Add one above or create follow-ups when adding contacts.
        </div>
      )}

      {!loading && tasks.length > 0 && (
        <div className="bg-white rounded-lg shadow divide-y">
          {tasks.map(task => {
            const dateInfo = formatDate(task.due_date)
            const isCompleted = task.status === 'completed'
            
            return (
              <div
                key={task.id}
                className={`px-6 py-4 flex items-center space-x-4 ${isCompleted ? 'bg-gray-50' : ''}`}
              >
                <button
                  onClick={() => handleComplete(task.id)}
                  disabled={isCompleted}
                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                    isCompleted 
                      ? 'bg-green-500 border-green-500 text-white' 
                      : 'border-gray-300 hover:border-green-500'
                  }`}
                >
                  {isCompleted && (
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>
                
                <div className="flex-1">
                  <p className={`font-medium ${isCompleted ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                    {task.title}
                  </p>
                  {task.contact_name && (
                    <p className="text-sm text-gray-500">{task.contact_name}</p>
                  )}
                </div>
                
                {dateInfo && (
                  <span className={`text-sm font-medium ${dateInfo.className}`}>
                    {dateInfo.text}
                  </span>
                )}
                
                <button
                  onClick={() => handleDelete(task.id)}
                  className="text-gray-400 hover:text-red-500"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default TasksPage
