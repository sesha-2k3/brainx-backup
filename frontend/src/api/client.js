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
