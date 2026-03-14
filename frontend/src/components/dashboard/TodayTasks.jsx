// TodayTasks.jsx — Tasks due today widget

import { Link } from 'react-router-dom'
import { completeTask } from '../../api/client'

function TodayTasks({ tasks = [], onTaskComplete }) {
  // Filter tasks due today or overdue
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const todayTasks = tasks.filter(task => {
    if (!task.due_date || task.status === 'completed') return false
    const dueDate = new Date(task.due_date)
    dueDate.setHours(0, 0, 0, 0)
    return dueDate <= today
  }).slice(0, 5)

  const handleComplete = async (taskId) => {
    try {
      await completeTask(taskId)
      onTaskComplete?.(taskId)
    } catch (err) {
      console.error('Failed to complete task:', err)
    }
  }

  const isOverdue = (dateStr) => {
    const due = new Date(dateStr)
    due.setHours(0, 0, 0, 0)
    return due < today
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>
          Today's Tasks
        </h3>
        <Link 
          to="/tasks"
          className="text-sm font-medium"
          style={{ color: 'var(--color-primary)' }}
        >
          View All →
        </Link>
      </div>

      {todayTasks.length === 0 ? (
        <div 
          className="text-center py-6"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          <p className="text-sm">No tasks due today</p>
        </div>
      ) : (
        <div className="space-y-2">
          {todayTasks.map(task => (
            <div 
              key={task.id}
              className="flex items-center p-3 rounded-lg group hover:bg-secondary transition-colors"
            >
              <button
                onClick={() => handleComplete(task.id)}
                className="w-5 h-5 rounded-full border-2 flex-shrink-0 mr-3 flex items-center justify-center transition-colors"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <span className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <svg className="w-3 h-3" style={{ color: 'var(--color-success)' }} fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </span>
              </button>
              
              <div className="flex-1 min-w-0">
                <p 
                  className="font-medium truncate"
                  style={{ color: 'var(--color-text)' }}
                >
                  {task.title}
                </p>
                {task.contact_name && (
                  <p 
                    className="text-sm truncate"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {task.contact_name}
                  </p>
                )}
              </div>

              {isOverdue(task.due_date) && (
                <span 
                  className="text-xs font-medium px-2 py-0.5 rounded"
                  style={{ 
                    backgroundColor: 'rgba(239, 68, 68, 0.1)', 
                    color: 'var(--color-error)' 
                  }}
                >
                  Overdue
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Quick add */}
      <button
        className="w-full mt-3 py-2 text-sm font-medium rounded-lg border-2 border-dashed transition-colors hover:bg-secondary"
        style={{ 
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-secondary)'
        }}
      >
        + Add Task
      </button>
    </div>
  )
}

export default TodayTasks
