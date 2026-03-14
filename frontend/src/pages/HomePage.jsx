// HomePage.jsx — Dashboard view with widgets

import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { listContacts, listTasks, getDueReminders, confirmProposal } from '../api/client'
import GreetingCard from '../components/dashboard/GreetingCard'
import WeekCalendar from '../components/dashboard/WeekCalendar'
import TodayTasks from '../components/dashboard/TodayTasks'
import DueReminders from '../components/dashboard/DueReminders'
import RecentContacts from '../components/dashboard/RecentContacts'
import ExtractionPreview from '../components/ExtractionPreview'

function HomePage() {
  const location = useLocation()
  const [loading, setLoading] = useState(true)
  const [contacts, setContacts] = useState([])
  const [tasks, setTasks] = useState([])
  const [dueReminders, setDueReminders] = useState([])
  
  // Handle extraction preview from quick capture
  const [extracted, setExtracted] = useState(location.state?.extracted || null)
  const [proposalId, setProposalId] = useState(location.state?.proposalId || null)
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      const [contactsRes, tasksRes, remindersRes] = await Promise.all([
        listContacts({ limit: 10 }),
        listTasks(),
        getDueReminders(),
      ])
      
      setContacts(contactsRes.contacts || [])
      setTasks(tasksRes.tasks || [])
      setDueReminders(remindersRes.contacts || [])
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleTaskComplete = (taskId) => {
    setTasks(tasks.filter(t => t.id !== taskId))
  }

  const handleMarkContacted = (contactId) => {
    setDueReminders(dueReminders.filter(c => c.id !== contactId))
  }

  const handleConfirm = async (formData) => {
    setError(null)
    try {
      const result = await confirmProposal(proposalId, formData)
      setExtracted(null)
      setProposalId(null)
      setSuccess(`Saved ${result.contact_name}${result.tasks_created ? ` with ${result.tasks_created} task(s)` : ''}`)
      loadDashboardData() // Refresh data
    } catch (err) {
      setError(err.message || 'Failed to save contact')
    }
  }

  const handleCancel = () => {
    setExtracted(null)
    setProposalId(null)
  }

  // Show extraction preview if coming from quick capture
  if (extracted) {
    return (
      <div className="space-y-6">
        <GreetingCard />
        
        {error && (
          <div 
            className="px-4 py-3 rounded-lg"
            style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-error)' }}
          >
            {error}
          </div>
        )}
        
        <ExtractionPreview
          data={extracted}
          proposalId={proposalId}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <GreetingCard />

      {/* Success message */}
      {success && (
        <div 
          className="px-4 py-3 rounded-lg flex items-center justify-between"
          style={{ backgroundColor: 'rgba(16, 185, 129, 0.1)', color: 'var(--color-success)' }}
        >
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="text-lg">&times;</button>
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="card h-48 animate-pulse" style={{ backgroundColor: 'var(--color-bg-secondary)' }} />
            <div className="card h-64 animate-pulse" style={{ backgroundColor: 'var(--color-bg-secondary)' }} />
          </div>
          <div className="space-y-6">
            <div className="card h-48 animate-pulse" style={{ backgroundColor: 'var(--color-bg-secondary)' }} />
            <div className="card h-48 animate-pulse" style={{ backgroundColor: 'var(--color-bg-secondary)' }} />
          </div>
        </div>
      ) : (
        <>
          {/* Recent Contacts Row */}
          <RecentContacts contacts={contacts} />

          {/* Main grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column - Calendar & Tasks */}
            <div className="lg:col-span-2 space-y-6">
              <WeekCalendar tasks={tasks} />
              <TodayTasks 
                tasks={tasks} 
                onTaskComplete={handleTaskComplete}
              />
            </div>

            {/* Right column - Reminders */}
            <div className="space-y-6">
              <DueReminders 
                contacts={dueReminders}
                onMarkContacted={handleMarkContacted}
              />

              {/* Quick Stats */}
              <div className="card p-4">
                <h3 className="font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
                  Quick Stats
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span style={{ color: 'var(--color-text-secondary)' }}>Total Contacts</span>
                    <span className="font-semibold" style={{ color: 'var(--color-text)' }}>{contacts.length}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span style={{ color: 'var(--color-text-secondary)' }}>Pending Tasks</span>
                    <span className="font-semibold" style={{ color: 'var(--color-text)' }}>
                      {tasks.filter(t => t.status === 'pending').length}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span style={{ color: 'var(--color-text-secondary)' }}>Due Reminders</span>
                    <span className="font-semibold" style={{ color: 'var(--color-accent-gold)' }}>
                      {dueReminders.length}
                    </span>
                  </div>
                </div>
              </div>

              {/* Keyboard shortcuts hint */}
              <div 
                className="card p-4 text-sm"
                style={{ backgroundColor: 'var(--color-bg-secondary)' }}
              >
                <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                  Keyboard Shortcuts
                </h4>
                <div className="space-y-1" style={{ color: 'var(--color-text-muted)' }}>
                  <div className="flex justify-between">
                    <span>Quick Search</span>
                    <kbd className="px-1.5 py-0.5 rounded bg-surface text-xs">⌘K</kbd>
                  </div>
                  <div className="flex justify-between">
                    <span>Quick Capture</span>
                    <kbd className="px-1.5 py-0.5 rounded bg-surface text-xs">⌘N</kbd>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default HomePage
