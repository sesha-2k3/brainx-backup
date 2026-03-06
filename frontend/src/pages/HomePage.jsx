import { useState } from 'react'
import { processText, processFile, confirmProposal } from '../api/client'
import ExtractionPreview from '../components/ExtractionPreview'

function HomePage() {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [extracted, setExtracted] = useState(null)
  const [proposalId, setProposalId] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleTextSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await processText(text)
      setExtracted(result.extracted)
      setProposalId(result.proposal_id)
      setText('')
    } catch (err) {
      setError(err.message || 'Failed to process text')
    } finally {
      setLoading(false)
    }
  }

  const handleFileSubmit = async (e) => {
    e.preventDefault()
    if (!file) return

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await processFile(file)
      setExtracted(result.extracted)
      setProposalId(result.proposal_id)
      setFile(null)
    } catch (err) {
      setError(err.message || 'Failed to process file')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (formData) => {
    try {
      const result = await confirmProposal(proposalId, formData)
      setExtracted(null)
      setProposalId(null)
      setSuccess(`Saved ${result.contact_name}${result.tasks_created ? ` with ${result.tasks_created} task(s)` : ''}`)
    } catch (err) {
      setError(err.message || 'Failed to save contact')
    }
  }

  const handleCancel = () => {
    setExtracted(null)
    setProposalId(null)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Add Interaction</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {success}
        </div>
      )}

      {extracted ? (
        <ExtractionPreview
          data={extracted}
          proposalId={proposalId}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      ) : (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          {/* Text Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter contact details or meeting notes
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Paste meeting notes, voice transcripts, or describe an interaction (Including business cards). Tasks, Contact info and reminders will be extracted automatically."
            />
            <button
              onClick={handleTextSubmit}
              disabled={loading || !text.trim()}
              className="mt-3 px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-blue-300"
            >
              {loading ? 'Processing...' : 'Extract Contact'}
            </button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">or upload a file</span>
            </div>
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload voice note or business card image
            </label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
              accept=".mp3,.wav,.ogg,.m4a,.png,.jpg,.jpeg"
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <p className="mt-1 text-xs text-gray-500">Supports: MP3, WAV, OGG, M4A, PNG, JPG</p>
            {file && (
              <button
                onClick={handleFileSubmit}
                disabled={loading}
                className="mt-3 px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-blue-300"
              >
                {loading ? 'Processing...' : 'Upload & Extract'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default HomePage