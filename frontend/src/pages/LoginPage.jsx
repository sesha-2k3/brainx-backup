// pages/LoginPage.jsx

import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/authContext'

// ── Tiny inline SVG icons (no extra dep) ─────────────────────────────────────

function EyeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
      <line x1="2" x2="22" y1="2" y2="22" />
    </svg>
  )
}

// ── Reusable show/hide password field ────────────────────────────────────────

function PasswordInput({ id, value, onChange, onFocus, onBlur, autoComplete, placeholder, hasError }) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <input
        id={id}
        type={visible ? 'text' : 'password'}
        autoComplete={autoComplete}
        required
        value={value}
        onChange={onChange}
        onFocus={onFocus}
        onBlur={onBlur}
        placeholder={placeholder}
        className={`input pr-10 ${hasError ? 'border-red-400 focus:border-red-400 dark:border-red-500' : ''}`}
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setVisible(v => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors"
        aria-label={visible ? 'Hide password' : 'Show password'}
      >
        {visible ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  )
}

// ── Shake keyframes (injected once into <head>) ───────────────────────────────

const SHAKE_CSS = `
  @keyframes shake {
    0%,100% { transform: translateX(0); }
    15%      { transform: translateX(-7px); }
    30%      { transform: translateX(7px); }
    45%      { transform: translateX(-4px); }
    60%      { transform: translateX(4px); }
    75%      { transform: translateX(-2px); }
    90%      { transform: translateX(2px); }
  }
  .shake { animation: shake 0.45s ease-out; }
`

// ── LoginPage ─────────────────────────────────────────────────────────────────

export default function LoginPage() {
  const { login }    = useAuth()
  const navigate     = useNavigate()
  const location     = useLocation()
  const from         = location.state?.from?.pathname || '/'
  const emailRef        = useRef(null)
  const formRef         = useRef(null)
  // Tracks whether the user has manually focused a field.
  // Auto-focus on mount triggers a blur when clicking away (e.g. "Create one")
  // before the user has typed anything — we ignore that first phantom blur.
  const userFocused     = useRef({ email: false, password: false })

  const [email,        setEmail]        = useState('')
  const [password,     setPassword]     = useState('')
  const [rememberMe,   setRememberMe]   = useState(false)
  const [error,        setError]        = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Inline validation — only fires after a field has been blurred
  const [touched, setTouched] = useState({ email: false, password: false })
  const emailError    = touched.email    && !email    ? 'Email is required'    : ''
  const passwordError = touched.password && !password ? 'Password is required' : ''

  // Auto-focus on mount
  useEffect(() => { emailRef.current?.focus() }, [])

  function triggerShake() {
    formRef.current?.classList.remove('shake')
    void formRef.current?.offsetWidth   // force reflow to restart animation
    formRef.current?.classList.add('shake')
  }

  function handleFocus(field) {
    userFocused.current[field] = true
  }

  function handleBlur(field) {
    // Ignore blur if the user never manually focused this field —
    // prevents the auto-focused email field from showing an error
    // when the user clicks a navigation link before typing anything.
    if (!userFocused.current[field]) return
    setTouched(t => ({ ...t, [field]: true }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setTouched({ email: true, password: true })

    if (!email || !password) {
      triggerShake()
      return
    }

    setError('')
    setIsSubmitting(true)

    try {
      await login({ email, password, rememberMe })
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Incorrect email or password')
      triggerShake()
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <style>{SHAKE_CSS}</style>

      <div className="min-h-screen flex items-center justify-center bg-app px-4">
        <div ref={formRef} className="card w-full max-w-sm p-8 animate-scale-in">

          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Welcome back</h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">Sign in to your BrainX account</p>
          </div>

          {/* Error banner */}
          {error && (
            <div className="mb-4 rounded-lg px-4 py-3 text-sm bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800 animate-fade-in">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">

            {/* Email */}
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                Email
              </label>
              <input
                ref={emailRef}
                id="login-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                onFocus={() => handleFocus('email')}
                onBlur={() => handleBlur('email')}
                placeholder="you@example.com"
                className={`input ${emailError ? 'border-red-400 focus:border-red-400 dark:border-red-500' : ''}`}
              />
              {emailError && (
                <p className="mt-1 text-xs text-red-500 animate-fade-in">{emailError}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="login-password" className="text-sm font-medium text-gray-700 dark:text-slate-300">
                  Password
                </label>
                {/* Hook up to a real route when you build forgot-password */}
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => {/* TODO: navigate('/forgot-password') */}}
                >
                  Forgot password?
                </button>
              </div>
              <PasswordInput
                id="login-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onFocus={() => handleFocus('password')}
                onBlur={() => handleBlur('password')}
                autoComplete="current-password"
                placeholder="••••••••"
                hasError={!!passwordError}
              />
              {passwordError && (
                <p className="mt-1 text-xs text-red-500 animate-fade-in">{passwordError}</p>
              )}
            </div>

            {/* Remember me */}
            <label className="flex items-center gap-2.5 cursor-pointer select-none w-fit">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={e => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 dark:border-slate-600 accent-primary"
              />
              <span className="text-sm text-gray-600 dark:text-slate-400">Stay signed in for 30 days</span>
            </label>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
            >
              {isSubmitting
                ? <><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Signing in…</>
                : 'Sign in'
              }
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-slate-400">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-medium">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </>
  )
}