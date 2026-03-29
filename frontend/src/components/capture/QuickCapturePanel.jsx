// QuickCapturePanel.jsx — Slide-up panel for quick input

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { processText, processFile, confirmProposal } from '../../api/client'

const TABS = [
  { id: 'text', label: 'Text', icon: TextIcon },
  { id: 'voice', label: 'Voice', icon: MicIcon },
  { id: 'file', label: 'File', icon: FileIcon },
]

function TextIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  )
}

function MicIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function QuickCapturePanel({ isOpen, onClose, onSuccess }) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('text')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [extracted, setExtracted] = useState(null)
  const [proposalId, setProposalId] = useState(null)
  
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  // Focus textarea when panel opens
  useEffect(() => {
    if (isOpen && activeTab === 'text' && textareaRef.current) {
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }, [isOpen, activeTab])

  // Reset state when closing
  useEffect(() => {
    if (!isOpen) {
      setText('')
      setFile(null)
      setError(null)
      setExtracted(null)
      setProposalId(null)
    }
  }, [isOpen])

  const handleTextSubmit = async () => {
    if (!text.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await processText(text)
      setExtracted(result.extracted)
      setProposalId(result.proposal_id)
    } catch (err) {
      setError(err.message || 'Failed to process text')
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = async (e) => {
    const selectedFile = e.target.files[0]
    if (!selectedFile) return
    
    setFile(selectedFile)
    setLoading(true)
    setError(null)
    
    try {
      const result = await processFile(selectedFile)
      setExtracted(result.extracted_data)
      setProposalId(result.id)
    } catch (err) {
      setError(err.message || 'Failed to process file')
      setFile(null)
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!extracted || !proposalId) return
    
    setLoading(true)
    setError(null)
    
    try {
      await confirmProposal(proposalId, {
        ...extracted,
        tasks: extracted.tasks || []
      })
      onSuccess?.()
      onClose()
      // Navigate to /contacts so the list remounts and shows the new contact.
      // Using navigate(0) would also work but causes a full page reload.
      navigate('/contacts')
    } catch (err) {
      setError(err.message || 'Failed to save')
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetails = () => {
    // Capture values before onClose() wipes them via the isOpen=false effect
    const snapshot = { extracted, proposalId }
    navigate('/add-contact', { state: snapshot })
    onClose()
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-50 bg-black/50 animate-fade-in"
        onClick={onClose}
      />

      {/* Panel */}
      <div 
        className="fixed bottom-0 left-0 right-0 z-50 animate-slide-up"
        style={{ 
          backgroundColor: 'var(--color-surface)',
          borderTopLeftRadius: '1rem',
          borderTopRightRadius: '1rem',
          maxHeight: '80vh',
        }}
      >
        {/* Handle bar */}
        <div className="flex justify-center pt-3 pb-2">
          <div 
            className="w-10 h-1 rounded-full"
            style={{ backgroundColor: 'var(--color-border)' }}
          />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 pb-3">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
            Quick Capture
          </h2>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-secondary"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        {!extracted && (
          <div className="flex px-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`
                  flex items-center space-x-2 px-4 py-3 border-b-2 font-medium text-sm
                  transition-colors
                `}
                style={{
                  borderColor: activeTab === id ? 'var(--color-primary)' : 'transparent',
                  color: activeTab === id ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                }}
              >
                <Icon />
                <span>{label}</span>
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {error && (
            <div 
              className="mb-4 px-4 py-3 rounded-lg text-sm"
              style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-error)' }}
            >
              {error}
            </div>
          )}

          {extracted ? (
            // Extraction preview
            <div className="space-y-4">
              <div 
                className="p-4 rounded-lg"
                style={{ backgroundColor: 'var(--color-bg-secondary)' }}
              >
                <h3 className="font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
                  {extracted.name}
                </h3>
                <div className="space-y-1 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  {extracted.company && <p>{extracted.role ? `${extracted.role} at ` : ''}{extracted.company}</p>}
                  {extracted.email && <p>{extracted.email}</p>}
                  {extracted.phone && <p>{extracted.phone}</p>}
                  {extracted.interaction_summary && (
                    <p className="mt-2 italic">"{extracted.interaction_summary}"</p>
                  )}
                  {extracted.tasks?.length > 0 && (
                    <p className="mt-2">{extracted.tasks.length} task(s) to create</p>
                  )}
                </div>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={handleViewDetails}
                  className="flex-1 btn-secondary py-3"
                >
                  Edit Details
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={loading}
                  className="flex-1 btn-primary py-3"
                >
                  {loading ? 'Saving...' : 'Save Contact'}
                </button>
              </div>
            </div>
          ) : (
            // Input forms
            <>
              {activeTab === 'text' && (
                <div className="space-y-4">
                  <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Paste meeting notes, describe an interaction, or enter contact details..."
                    rows={4}
                    className="input resize-none"
                    style={{ minHeight: '120px' }}
                  />
                  <button
                    onClick={handleTextSubmit}
                    disabled={loading || !text.trim()}
                    className="w-full btn-primary py-3"
                  >
                    {loading ? 'Processing...' : 'Extract Contact'}
                  </button>
                </div>
              )}

              {activeTab === 'voice' && (
                <div className="text-center py-8">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-20 h-20 rounded-full mx-auto flex items-center justify-center"
                    style={{ backgroundColor: 'var(--color-primary-light)' }}
                  >
                    <MicIcon />
                  </button>
                  <p className="mt-4 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    Upload a voice recording
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </div>
              )}

              {activeTab === 'file' && (
                <div 
                  className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-secondary transition-colors"
                  style={{ borderColor: 'var(--color-border)' }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileIcon />
                  <p className="mt-2 font-medium" style={{ color: 'var(--color-text)' }}>
                    {file ? file.name : 'Click to upload'}
                  </p>
                  <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
                    Business card image or voice note
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,audio/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Keyboard hint */}
        <div 
          className="px-4 py-2 text-center text-xs border-t"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
        >
          Press <kbd className="px-1.5 py-0.5 rounded bg-secondary">Esc</kbd> to close
        </div>
      </div>
    </>
  )
}

export default QuickCapturePanel