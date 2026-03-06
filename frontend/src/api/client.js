// API: Client functions for backend communication

const API_BASE = '/api'

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  return response.json()
}

// Input processing
export async function processText(text) {
  return request('/input/text', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export async function processFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`${API_BASE}/input/file`, {
    method: 'POST',
    body: formData,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }
  
  return response.json()
}

// Proposals
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

// Contacts
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

// Contact reminders
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

// Tasks
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

// Search
export async function search(query) {
  return request(`/search?q=${encodeURIComponent(query)}`)
}

// Search contacts (semantic)
export async function searchContacts(query) {
  return request(`/search?q=${encodeURIComponent(query)}`)
}

// update task function
export async function updateTask(taskId, taskData) {
  return request(`/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(taskData),
  })
}

// Interaction Handling (CRUD)
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