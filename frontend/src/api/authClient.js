// API: Auth-specific client functions (/auth/*)
// These do NOT go through the shared request() helper because they must
// work without a token (and they handle the token themselves).

const API_BASE = '/brainx/api'

async function authRequest(endpoint, body) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const data = await response.json().catch(() => ({ detail: 'Request failed' }))

  if (!response.ok) {
    throw new Error(data.detail || 'Request failed')
  }

  return data
}

/**
 * Register a new account.
 * @returns {{ access_token: string, token_type: string }}
 */
export async function registerUser({ email, password }) {
  return authRequest('/auth/register', { email, password })
}

/**
 * Log in with email + password.
 * @returns {{ access_token: string, token_type: string }}
 */
export async function loginUser({ email, password }) {
  return authRequest('/auth/login', { email, password })
}

/**
 * Fetch the profile of the currently authenticated user.
 * Requires a valid Bearer token to be stored already.
 * @returns {{ id: string, email: string, is_active: boolean }}
 */
export async function fetchMe(token) {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch user profile')
  }

  return response.json()
}