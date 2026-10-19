// src/hooks/useAuth.jsx
import { createContext, useContext, useState, useEffect } from 'react'

const Ctx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const u = localStorage.getItem('sk_user')
    const t = localStorage.getItem('sk_token')
    if (u && t) { try { setUser(JSON.parse(u)) } catch {} }
    setLoading(false)
  }, [])

  const login = (userData, token) => {
    sessionStorage.removeItem('sk_chat_session_id')
    localStorage.setItem('sk_token', token)
    localStorage.setItem('sk_user', JSON.stringify(userData))
    setUser(userData)
  }

  const logout = () => {
    sessionStorage.removeItem('sk_chat_session_id')
    localStorage.removeItem('sk_token')
    localStorage.removeItem('sk_user')
    setUser(null)
  }

  return <Ctx.Provider value={{ user, login, logout, loading }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
