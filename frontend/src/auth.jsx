import { createContext, useContext, useState } from 'react'

const TOKEN_KEY = 'gop-token'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))

  async function signIn(username, password) {
    const response = await fetch('/api/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (response.status === 400) throw new Error('Wrong username or password.')
    if (!response.ok) throw new Error('Sign in failed. Try again later.')
    const data = await response.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    setToken(data.token)
  }

  async function signOut() {
    // Forget the token locally even if the server can't be reached, so the
    // button always does what it says on this device.
    try {
      await fetch('/api/auth/logout/', {
        method: 'POST',
        headers: { Authorization: `Token ${token}` },
      })
    } finally {
      localStorage.removeItem(TOKEN_KEY)
      setToken(null)
    }
  }

  return (
    <AuthContext.Provider value={{ token, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

// The hook lives beside its provider; the cost is only a full reload when this file is edited.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
