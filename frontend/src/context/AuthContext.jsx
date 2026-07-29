// context/AuthContext.jsx
// Provides: useAuth() → { user, token, isLoading, login, register, logout }

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { fetchMe, loginUser, registerUser } from '../api/authClient'
import { tokenStorage } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,        setUser]        = useState(null)
  const [token,       setToken]       = useState(() => tokenStorage.get())
  const [isLoading,   setIsLoading]   = useState(true)

  // On mount: validate any stored token by hitting /auth/me.
  // This keeps the session alive across hard refreshes.
  useEffect(() => {
    async function restoreSession() {
      const stored = tokenStorage.get()
      if (!stored) { setIsLoading(false); return }

      try {
        const me = await fetchMe(stored)
        setUser(me)
        setToken(stored)
      } catch {
        // Expired or invalid — wipe storage so user lands on /login
        tokenStorage.remove()
        setToken(null)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }
    restoreSession()
  }, [])

  const applyToken = useCallback(async (newToken) => {
    tokenStorage.set(newToken)
    setToken(newToken)
    const me = await fetchMe(newToken)
    setUser(me)
  }, [])

  /**
   * Register a new account. Logs the user in immediately after.
   */
  const register = useCallback(async ({ email, password }) => {
    const { access_token } = await registerUser({ email, password })
    await applyToken(access_token)
  }, [applyToken])

  /**
   * Log in with email + password.
   *
   * @param {boolean} rememberMe — when true, the backend issues a long-lived
   *   token (settings.remember_me_expire_minutes, 30 days by default) instead
   *   of the standard 24-hour one. authClient maps this to the `remember_me`
   *   body field that LoginRequest declares.
   */
  const login = useCallback(async ({ email, password, rememberMe = false }) => {
    const { access_token } = await loginUser({ email, password, rememberMe })
    await applyToken(access_token)
  }, [applyToken])

  const logout = useCallback(() => {
    tokenStorage.remove()
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
