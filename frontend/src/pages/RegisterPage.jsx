// pages/RegisterPage.jsx

import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// ── SVG icons ─────────────────────────────────────────────────────────────────

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

function CheckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

// ── Password input with show/hide ────────────────────────────────────────────

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

// ── Password strength logic ───────────────────────────────────────────────────
//  Returns { score: 0–4, label, color }

const STRENGTH_RULES = [
  { test: (p) => p.length >= 8,                    label: '8+ characters' },
  { test: (p) => /[A-Z]/.test(p),                  label: 'Uppercase letter' },
  { test: (p) => /[0-9]/.test(p),                  label: 'Number' },
  { test: (p) => /[^A-Za-z0-9]/.test(p),           label: 'Symbol' },
]

function getStrength(password) {
  if (!password) return { score: 0, label: '', color: '' }
  const passed = STRENGTH_RULES.filter(r => r.test(password)).length
  if (passed <= 1) return { score: 1, label: 'Weak',   color: 'bg-red-400' }
  if (passed === 2) return { score: 2, label: 'Fair',   color: 'bg-yellow-400' }
  if (passed === 3) return { score: 3, label: 'Good',   color: 'bg-blue-400' }
  return              { score: 4, label: 'Strong', color: 'bg-green-500' }
}

function PasswordStrengthBar({ password }) {
  const { score, label, color } = getStrength(password)
  if (!password) return null

  return (
    <div className="mt-2 space-y-1.5 animate-fade-in">
      {/* Bar */}
      <div className="flex gap-1">
        {[1, 2, 3, 4].map(i => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i <= score ? color : 'bg-gray-200 dark:bg-gray-700'
            }`}
          />
        ))}
      </div>

      {/* Rules checklist */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        {STRENGTH_RULES.map(rule => {
          const ok = rule.test(password)
          return (
            <span
              key={rule.label}
              className={`flex items-center gap-1 text-xs transition-colors ${
                ok ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-slate-500'
              }`}
            >
              <span className={`flex-shrink-0 w-3 h-3 rounded-full flex items-center justify-center ${
                ok ? 'bg-green-500 text-white' : 'border border-current opacity-40'
              }`}>
                {ok && <CheckIcon />}
              </span>
              {rule.label}
            </span>
          )
        })}
      </div>
    </div>
  )
}

// ── Shake CSS ─────────────────────────────────────────────────────────────────

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

// ── RegisterPage ──────────────────────────────────────────────────────────────

export default function RegisterPage() {
  const { register }  = useAuth()
  const navigate      = useNavigate()
  const emailRef      = useRef(null)
  const formRef       = useRef(null)
  const userFocused   = useRef({ email: false, password: false, confirm: false })

  const [email,        setEmail]        = useState('')
  const [password,     setPassword]     = useState('')
  const [confirm,      setConfirm]      = useState('')
  const [error,        setError]        = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [touched, setTouched] = useState({ email: false, password: false, confirm: false })

  const emailError    = touched.email    && !email    ? 'Email is required' : ''
  const passwordError = touched.password && password.length > 0 && password.length < 8
    ? 'At least 8 characters required'
    : touched.password && !password ? 'Password is required' : ''
  const confirmError  = touched.confirm  && confirm !== password ? 'Passwords do not match' : ''

  // Auto-focus on mount
  useEffect(() => { emailRef.current?.focus() }, [])

  function triggerShake() {
    formRef.current?.classList.remove('shake')
    void formRef.current?.offsetWidth
    formRef.current?.classList.add('shake')
  }

  function handleFocus(field) {
    userFocused.current[field] = true
  }

  function handleBlur(field) {
    if (!userFocused.current[field]) return
    setTouched(t => ({ ...t, [field]: true }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setTouched({ email: true, password: true, confirm: true })

    if (!email || password.length < 8 || password !== confirm) {
      triggerShake()
      return
    }

    setError('')
    setIsSubmitting(true)

    try {
      await register({ email, password })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message || 'Registration failed')
      triggerShake()
    } finally {
      setIsSubmitting(false)
    }
  }

  const strength = getStrength(password)
  const canSubmit = email && password.length >= 8 && password === confirm

  return (
    <>
      <style>{SHAKE_CSS}</style>

      <div className="min-h-screen flex items-center justify-center bg-app px-4">
        <div ref={formRef} className="card w-full max-w-sm p-8 animate-scale-in">

          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Create account</h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">Get started with BrainX</p>
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
              <label htmlFor="reg-email" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                Email
              </label>
              <input
                ref={emailRef}
                id="reg-email"
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

            {/* Password + strength meter */}
            <div>
              <label htmlFor="reg-password" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                Password
              </label>
              <PasswordInput
                id="reg-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onFocus={() => handleFocus('password')}
                onBlur={() => handleBlur('password')}
                autoComplete="new-password"
                placeholder="••••••••"
                hasError={!!passwordError}
              />
              {passwordError && (
                <p className="mt-1 text-xs text-red-500 animate-fade-in">{passwordError}</p>
              )}
              <PasswordStrengthBar password={password} />
            </div>

            {/* Confirm password */}
            <div>
              <label htmlFor="reg-confirm" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                Confirm password
              </label>
              <PasswordInput
                id="reg-confirm"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                onFocus={() => handleFocus('confirm')}
                onBlur={() => handleBlur('confirm')}
                autoComplete="new-password"
                placeholder="••••••••"
                hasError={!!confirmError}
              />
              {confirmError && (
                <p className="mt-1 text-xs text-red-500 animate-fade-in">{confirmError}</p>
              )}
              {/* Match confirmation — show once user has typed something */}
              {confirm && !confirmError && (
                <p className="mt-1 text-xs text-green-600 dark:text-green-400 flex items-center gap-1 animate-fade-in">
                  <CheckIcon /> Passwords match
                </p>
              )}
            </div>

            {/* Submit — visually dims until form is valid */}
            <button
              type="submit"
              disabled={isSubmitting}
              className={`btn-primary w-full flex items-center justify-center gap-2 mt-2 transition-opacity ${
                !canSubmit && !isSubmitting ? 'opacity-60' : ''
              }`}
            >
              {isSubmitting
                ? <><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Creating account…</>
                : 'Create account'
              }
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </>
  )
}