import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, type AuthUser } from '@/lib/api'

interface AuthContextValue {
  user: AuthUser | null
  /** Distinguishes "checking session" from "not logged in" — a ProtectedRoute
   *  that ignores this flashes a /login redirect on every hard refresh. */
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // One session check on mount. `cancelled` guards against a late resolve
  // after unmount (React strict-mode double-invoke / fast navigation).
  useEffect(() => {
    let cancelled = false
    api.auth
      .me()
      .then(res => {
        if (!cancelled) setUser(res.user)
      })
      .catch(() => {
        // 401 (or network hiccup) → not authenticated. Never throw here.
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.auth.login(email, password)
    setUser(res.user)
  }, [])

  // Fire-and-forget: a failed server logout must never strand the user
  // "logged in" client-side. The cookie's Max-Age handles expiry regardless.
  const logout = useCallback(async () => {
    await api.auth.logout().catch(() => undefined)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
