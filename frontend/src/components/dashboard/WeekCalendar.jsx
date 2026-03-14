// WeekCalendar.jsx — Mini week view with task indicators

import { useMemo } from 'react'

function WeekCalendar({ tasks = [] }) {
  const weekDays = useMemo(() => {
    const today = new Date()
    const startOfWeek = new Date(today)
    const dayOfWeek = today.getDay()
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek // Start from Monday
    startOfWeek.setDate(today.getDate() + diff)

    const days = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek)
      date.setDate(startOfWeek.getDate() + i)
      days.push(date)
    }
    return days
  }, [])

  const getTasksForDate = (date) => {
    const dateStr = date.toISOString().split('T')[0]
    return tasks.filter(task => {
      if (!task.due_date) return false
      return task.due_date.split('T')[0] === dateStr
    })
  }

  const isToday = (date) => {
    const today = new Date()
    return date.toDateString() === today.toDateString()
  }

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>
          {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
        </h3>
        <button 
          className="text-sm font-medium"
          style={{ color: 'var(--color-primary)' }}
        >
          View Calendar →
        </button>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {/* Day names */}
        {dayNames.map((name, i) => (
          <div 
            key={name} 
            className="text-center text-xs font-medium py-1"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {name}
          </div>
        ))}

        {/* Day numbers */}
        {weekDays.map((date, i) => {
          const dayTasks = getTasksForDate(date)
          const today = isToday(date)
          
          return (
            <div 
              key={i}
              className={`
                relative text-center py-3 rounded-lg cursor-pointer
                transition-colors
                ${today ? '' : 'hover:bg-secondary'}
              `}
              style={today ? { 
                backgroundColor: 'var(--color-primary)',
                color: 'white'
              } : {
                color: 'var(--color-text)'
              }}
            >
              <span className="font-medium">{date.getDate()}</span>
              
              {/* Task indicator dot */}
              {dayTasks.length > 0 && (
                <div 
                  className={`
                    absolute bottom-1 left-1/2 -translate-x-1/2
                    w-1.5 h-1.5 rounded-full
                  `}
                  style={{ 
                    backgroundColor: today ? 'white' : 'var(--color-primary)' 
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default WeekCalendar
