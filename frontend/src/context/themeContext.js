// themeContext.js — context object + consumer hook. See authContext.js for why
// this is split from the provider component.

import { createContext, useContext } from 'react'

export const ThemeContext = createContext(null)

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within <ThemeProvider>')
  return ctx
}
