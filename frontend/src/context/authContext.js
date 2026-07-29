// authContext.js — context object + consumer hook.
//
// Separate from AuthProvider.jsx on purpose. Vite's Fast Refresh only preserves
// state for modules that export components exclusively; a module exporting both
// a component and a hook falls back to a full reload on every edit, which loses
// component state across saves. Keeping the hook here and the provider there
// means editing either one hot-reloads properly.

import { createContext, useContext } from 'react'

export const AuthContext = createContext(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
