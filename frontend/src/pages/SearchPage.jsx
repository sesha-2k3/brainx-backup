// SearchPage.jsx — Natural language search across contacts, tasks, and interactions

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { searchContacts } from '../api/client'

// Avatar colors
const avatarColors = {
  A: '#C43B3B', B: '#3B5DC9', C: '#2D8F4E', D: '#D4A03B',
  E: '#8B5CF6', F: '#EC4899', G: '#14B8A6', H: '#F97316',
}

const getAvatarColor = (name) => {
  const firstLetter = (name || 'A').charAt(0).toUpperCase()
  return avatarColors[firstLetter] || '#6B7280'
}

function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState({ 
    contacts: [], 
    tasks: [], 
    interactions: [],
    explanation: '',
  })
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    
    setLoading(true)
    setError(null)
    setHasSearched(true)
    
    try {
      const result = await searchContacts(query)
      setResults({
        contacts: result.contacts || [],
        tasks: result.tasks || [],
        interactions: result.interactions || [],
        explanation: result.explanation || '',
      })
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

  const totalResults = results.contacts.length + results.tasks.length + results.interactions.length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
          Search
        </h1>
        <p className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Ask questions about your contacts in natural language
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="card p-4">
        <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
          <div className="relative flex-1">
            <svg 
              className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5"
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
              style={{ color: 'var(--color-text-muted)' }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="E.g., Who did I meet at the conference last week?"
              className="input pl-10"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="btn-primary"
          >
            {loading ? (
              <span className="flex items-center space-x-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Searching...</span>
              </span>
            ) : 'Search'}
          </button>
        </div>
        
        {/* Example queries */}
        <div className="mt-3 flex flex-wrap gap-2">
          {exampleQueries.map(eq => (
            <button
              key={eq}
              type="button"
              onClick={() => setQuery(eq)}
              className="text-sm px-3 py-1 rounded-full transition-colors"
              style={{ 
                backgroundColor: 'var(--color-bg-secondary)',
                color: 'var(--color-text-secondary)'
              }}
            >
              {eq}
            </button>
          ))}
        </div>
      </form>

      {/* Error */}
      {error && (
        <div 
          className="px-4 py-3 rounded-lg"
          style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-error)' }}
        >
          {error}
        </div>
      )}

      {/* AI Explanation */}
      {results.explanation && (
        <div 
          className="card p-4 border-l-4"
          style={{ 
            backgroundColor: 'var(--color-primary-light)',
            borderLeftColor: 'var(--color-primary)'
          }}
        >
          <p className="text-sm" style={{ color: 'var(--color-text)' }}>
            {results.explanation}
          </p>
        </div>
      )}

      {/* Results */}
      {hasSearched && !loading && (
        <div className="space-y-6">
          {/* Results count */}
          {totalResults > 0 && (
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Found {totalResults} result{totalResults !== 1 ? 's' : ''}
            </p>
          )}

          {/* Contacts */}
          {results.contacts.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3" style={{ color: 'var(--color-text)' }}>
                Contacts ({results.contacts.length})
              </h2>
              <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
                {results.contacts.map(contact => (
                  <Link
                    key={contact.id}
                    to={`/contacts/${contact.id}`}
                    className="flex items-center px-4 py-3 hover:bg-secondary transition-colors"
                  >
                    <div 
                      className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold text-white mr-3 flex-shrink-0"
                      style={{ backgroundColor: getAvatarColor(contact.name) }}
                    >
                      {contact.name?.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="font-medium" style={{ color: 'var(--color-text)' }}>
                        {contact.name}
                      </h3>
                      <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        {[contact.role, contact.company].filter(Boolean).join(' at ')}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Interactions */}
          {results.interactions.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3" style={{ color: 'var(--color-text)' }}>
                Interactions ({results.interactions.length})
              </h2>
              <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
                {results.interactions.map(interaction => (
                  <div key={interaction.id} className="px-4 py-4">
                    <div className="flex items-center justify-between mb-2">
                      <Link 
                        to={`/contacts/${interaction.contact_id}`}
                        className="font-medium hover:underline"
                        style={{ color: 'var(--color-primary)' }}
                      >
                        {interaction.contact_name}
                      </Link>
                      <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                        {new Date(interaction.occurred_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p style={{ color: 'var(--color-text)' }}>{interaction.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tasks */}
          {results.tasks.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3" style={{ color: 'var(--color-text)' }}>
                Tasks ({results.tasks.length})
              </h2>
              <div className="card divide-y" style={{ borderColor: 'var(--color-border)' }}>
                {results.tasks.map(task => (
                  <div key={task.id} className="px-4 py-4">
                    <p className="font-medium" style={{ color: 'var(--color-text)' }}>
                      {task.title}
                    </p>
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                      {task.contact_name && `${task.contact_name} • `}
                      {task.due_date 
                        ? `Due: ${new Date(task.due_date).toLocaleDateString()}` 
                        : 'No due date'
                      }
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No results */}
          {totalResults === 0 && (
            <div className="card p-12 text-center">
              <svg 
                className="w-16 h-16 mx-auto mb-4 opacity-50"
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
                style={{ color: 'var(--color-text-muted)' }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>
                No results found
              </p>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Try a different search query or check your spelling
              </p>
            </div>
          )}
        </div>
      )}

      {/* Initial state - before search */}
      {!hasSearched && (
        <div 
          className="card p-8 text-center"
          style={{ backgroundColor: 'var(--color-bg-secondary)' }}
        >
          <svg 
            className="w-16 h-16 mx-auto mb-4 opacity-50"
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>
            Search your CRM
          </p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Use natural language to find contacts, interactions, and tasks.<br />
            Try clicking one of the example queries above!
          </p>
        </div>
      )}
    </div>
  )
}

export default SearchPage
