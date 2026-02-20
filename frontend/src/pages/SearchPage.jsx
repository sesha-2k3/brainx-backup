// SearchPage: Natural language search across contacts and interactions

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { search } from '../api/client'

function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await search(query)
      setResults(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const exampleQueries = [
    'Who is Eddie?',
    'Investors I met this month',
    'What did we discuss with Acme Corp?',
    'Follow-ups due this week',
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Search</h1>

      {/* Search form */}
      <form onSubmit={handleSearch} className="bg-white rounded-lg shadow p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Ask a question about your contacts
        </label>
        <div className="flex space-x-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="E.g., Who did I meet at the conference last week?"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
        
        {/* Example queries */}
        <div className="mt-3 flex flex-wrap gap-2">
          {exampleQueries.map(eq => (
            <button
              key={eq}
              type="button"
              onClick={() => setQuery(eq)}
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              {eq}
            </button>
          ))}
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Contacts */}
          {results.contacts?.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                Contacts ({results.contacts.length})
              </h2>
              <div className="bg-white rounded-lg shadow divide-y">
                {results.contacts.map(contact => (
                  <Link
                    key={contact.id}
                    to={`/contacts/${contact.id}`}
                    className="block px-6 py-4 hover:bg-gray-50"
                  >
                    <h3 className="font-medium text-gray-900">{contact.name}</h3>
                    <p className="text-sm text-gray-500">
                      {[contact.role, contact.company].filter(Boolean).join(' at ')}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Interactions */}
          {results.interactions?.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                Interactions ({results.interactions.length})
              </h2>
              <div className="bg-white rounded-lg shadow divide-y">
                {results.interactions.map(interaction => (
                  <div key={interaction.id} className="px-6 py-4">
                    <div className="flex items-center justify-between mb-1">
                      <Link 
                        to={`/contacts/${interaction.contact_id}`}
                        className="font-medium text-blue-600 hover:underline"
                      >
                        {interaction.contact_name}
                      </Link>
                      <span className="text-sm text-gray-400">
                        {new Date(interaction.occurred_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-gray-700">{interaction.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tasks */}
          {results.tasks?.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                Tasks ({results.tasks.length})
              </h2>
              <div className="bg-white rounded-lg shadow divide-y">
                {results.tasks.map(task => (
                  <div key={task.id} className="px-6 py-4">
                    <p className="font-medium text-gray-900">{task.title}</p>
                    <p className="text-sm text-gray-500">
                      {task.contact_name && `${task.contact_name} • `}
                      {task.due_date ? `Due: ${new Date(task.due_date).toLocaleDateString()}` : 'No due date'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No results */}
          {!results.contacts?.length && !results.interactions?.length && !results.tasks?.length && (
            <div className="text-center py-12 text-gray-500">
              No results found for "{query}"
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SearchPage
