// HomePage: Main input page with text/file upload and extraction preview

import { useState } from 'react'
import { processText, processFile, confirmProposal, rejectProposal } from '../api/client'
import ExtractionPreview from '../components/ExtractionPreview'

function HomePage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [proposal, setProposal] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleTextSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return
    
    setLoading(true)
    setError(null)
    setSuccess(null)
    
    try {
      const result = await processText(text)
      setProposal(result)
      setText('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    setLoading(true)
    setError(null)
    setSuccess(null)
    
    try {
      const result = await processFile(file)
      setProposal(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      e.target.value = ''
    }
  }

  const handleConfirm = async (editedData) => {
    if (!proposal) return
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await confirmProposal(proposal.id, editedData)
      setProposal(null)
      setSuccess(`Saved: ${result.contact.name}`)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!proposal) return
    
    try {
      await rejectProposal(proposal.id)
    } catch (err) {
      // Ignore errors on cancel
    }
    setProposal(null)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Add Contact</h1>
      
      {/* Success message */}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {success}
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Input form - hide when showing proposal */}
      {!proposal && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          {/* Text input */}
          <form onSubmit={handleTextSubmit}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter contact details or meeting notes
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="E.g., Met John Smith from Acme Corp at the conference. He's a VP of Sales, interested in partnership. Email: john@acme.com. Follow up next week about proposal."
              rows={5}
              className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="mt-3 bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Extract Contact'}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center">
            <div className="flex-1 border-t border-gray-200"></div>
            <span className="px-4 text-sm text-gray-500">or upload a file</span>
            <div className="flex-1 border-t border-gray-200"></div>
          </div>

          {/* File upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload voice note or business card image
            </label>
            <input
              type="file"
              accept="audio/*,image/*"
              onChange={handleFileUpload}
              disabled={loading}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            />
            <p className="mt-1 text-sm text-gray-500">
              Supports: MP3, WAV, OGG, M4A, PNG, JPG
            </p>
          </div>
        </div>
      )}

      {/* Extraction preview */}
      {proposal && (
        <ExtractionPreview
          proposal={proposal}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          loading={loading}
        />
      )}
    </div>
  )
}

export default HomePage
