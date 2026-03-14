// Layout.jsx — Main shell component with responsive navigation

import { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import BottomNav from './BottomNav'
import QuickCaptureButton from '../capture/QuickCaptureButton'
import QuickCapturePanel from '../capture/QuickCapturePanel'
import CommandBar from '../CommandBar'

function Layout({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [captureOpen, setCaptureOpen] = useState(false)
  const [commandBarOpen, setCommandBarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  // Check for mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd/Ctrl + K for command bar
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandBarOpen(true)
      }
      
      // Cmd/Ctrl + N for quick capture
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault()
        setCaptureOpen(true)
      }
      
      // Escape to close
      if (e.key === 'Escape') {
        setCaptureOpen(false)
        setCommandBarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleCaptureSuccess = () => {
    setCaptureOpen(false)
    // Could trigger a refresh of dashboard data here
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Sidebar - hidden on mobile */}
      {!isMobile && (
        <Sidebar 
          collapsed={sidebarCollapsed} 
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
        />
      )}

      {/* Main content area */}
      <main 
        className={`
          min-h-screen transition-all duration-200
          ${!isMobile ? (sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-60') : ''}
          ${isMobile ? 'pb-20' : ''}
        `}
      >
        <div className="max-w-6xl mx-auto px-4 py-6 lg:px-8 lg:py-8">
          {children}
        </div>
      </main>

      {/* Mobile bottom navigation */}
      {isMobile && (
        <BottomNav onCaptureClick={() => setCaptureOpen(true)} />
      )}

      {/* Desktop floating capture button */}
      {!isMobile && (
        <QuickCaptureButton onClick={() => setCaptureOpen(true)} />
      )}

      {/* Quick capture slide-up panel */}
      <QuickCapturePanel 
        isOpen={captureOpen} 
        onClose={() => setCaptureOpen(false)}
        onSuccess={handleCaptureSuccess}
      />

      {/* Command bar (Cmd+K) */}
      <CommandBar 
        isOpen={commandBarOpen} 
        onClose={() => setCommandBarOpen(false)} 
      />
    </div>
  )
}

export default Layout
