// API: Client functions for backend communication

const API_BASE = '/api'

// ── Token storage ─────────────────────────────────────────────────────────────
// A thin wrapper so the rest of the app never touches localStorage directly.
// Swap these two functions if you ever want to move to sessionStorage or cookies.

export const tokenStorage = {
  get: () => localStorage.getItem('access_token'),
  set: (token) => localStorage.setItem('access_token', token),
  remove: () => localStorage.removeItem('access_token'),
}

// ── Core request helper ───────────────────────────────────────────────────────

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30000) // 30s timeout

  // Attach the JWT if we have one — auth endpoints will simply ignore it
  const token = tokenStorage.get()
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {}

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
        ...options.headers,
      },
      signal: controller.signal,
      ...options,
    })

    clearTimeout(timeout)

    if (!response.ok) {
      // If the server says 401 (expired / invalid token) clear the stored token
      // so the AuthContext can pick it up and redirect to /login.
      if (response.status === 401) {
        tokenStorage.remove()
      }
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || 'Request failed')
    }

    return response.json()
  } catch (error) {
    clearTimeout(timeout)
    if (error.name === 'AbortError') {
      throw new Error('Request timeout')
    }
    throw error
  }
}

// ── Input processing ──────────────────────────────────────────────────────────

export async function processText(text) {
  return request('/input/text', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export async function processFile(file) {
  const formData = new FormData()
  formData.append('file', file)

  const token = tokenStorage.get()
  const response = await fetch(`${API_BASE}/input/file`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
    // No Content-Type — browser sets it automatically with the boundary for multipart
  })

  if (!response.ok) {
    if (response.status === 401) tokenStorage.remove()
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

// ── Proposals ─────────────────────────────────────────────────────────────────

export async function getProposal(id) {
  return request(`/proposals/${id}`)
}

export async function confirmProposal(id, data) {
  return request(`/proposals/${id}/confirm`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function rejectProposal(id) {
  return request(`/proposals/${id}`, {
    method: 'DELETE',
  })
}

// ── Contacts ──────────────────────────────────────────────────────────────────

export async function listContacts(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request(`/contacts${query ? `?${query}` : ''}`)
}

export async function getContact(id) {
  return request(`/contacts/${id}`)
}

export async function updateContact(id, data) {
  return request(`/contacts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteContact(id) {
  return request(`/contacts/${id}`, {
    method: 'DELETE',
  })
}

// ── Contact reminders ─────────────────────────────────────────────────────────

export async function setContactReminder(contactId, frequency) {
  return request(`/contacts/${contactId}/set-reminder?frequency=${frequency}`, {
    method: 'POST',
  })
}

export async function getDueReminders() {
  return request('/contacts/due-reminders')
}

export async function markContacted(contactId) {
  return request(`/contacts/${contactId}/mark-contacted`, {
    method: 'POST',
  })
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export async function listTasks(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request(`/tasks${query ? `?${query}` : ''}`)
}

export async function createTask(data) {
  return request('/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTask(taskId, taskData) {
  return request(`/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(taskData),
  })
}

export async function completeTask(id) {
  return request(`/tasks/${id}/complete`, {
    method: 'POST',
  })
}

export async function deleteTask(id) {
  return request(`/tasks/${id}`, {
    method: 'DELETE',
  })
}

// ── Search ────────────────────────────────────────────────────────────────────

export async function search(query) {
  return request(`/search?q=${encodeURIComponent(query)}`)
}

export async function searchContacts(query) {
  return request(`/search?q=${encodeURIComponent(query)}`)
}

// ── Interactions ──────────────────────────────────────────────────────────────

export async function createInteraction(data) {
  return request('/interactions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateInteraction(interactionId, data) {
  return request(`/interactions/${interactionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteInteraction(interactionId) {
  return request(`/interactions/${interactionId}`, {
    method: 'DELETE',
  })
}
