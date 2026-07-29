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
    const detail = data.detail
    const message = Array.isArray(detail)
      ? detail.map(e => e.msg.replace('Value error, ', '')).join(', ')
      : detail || 'Request failed'
    throw new Error(message)
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
 *
 * @param {boolean} [rememberMe] - requests a long-lived token. Sent as
 *   `remember_me` because that is the field name the backend's LoginRequest
 *   schema declares; a camelCase key is silently discarded by Pydantic.
 * @returns {{ access_token: string, token_type: string }}
 */
export async function loginUser({ email, password, rememberMe = false }) {
  return authRequest('/auth/login', { email, password, remember_me: rememberMe })
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