import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const TOKEN_KEY = 'gop-token'
const AuthContext = createContext(null)

function storeToken(token, setToken) {
  localStorage.setItem(TOKEN_KEY, token)
  setToken(token)
}

function authHeaders(token) {
  return {
    Authorization: `Token ${token}`,
    'Content-Type': 'application/json',
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [me, setMe] = useState(null)
  const [meStatus, setMeStatus] = useState(token ? 'loading' : 'idle')

  const refreshMe = useCallback(async (activeToken = token) => {
    if (!activeToken) {
      setMe(null)
      setMeStatus('idle')
      return null
    }
    setMeStatus('loading')
    try {
      const response = await fetch('/api/auth/me/', {
        headers: { Authorization: `Token ${activeToken}` },
      })
      if (response.status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setMe(null)
        setMeStatus('idle')
        return null
      }
      if (!response.ok) throw new Error('Could not load your account.')
      const data = await response.json()
      setMe(data)
      setMeStatus('ready')
      return data
    } catch (err) {
      setMeStatus('error')
      throw err
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      setMe(null)
      setMeStatus('idle')
      return
    }
    refreshMe(token).catch(() => {})
  }, [token, refreshMe])

  async function signIn(username, password) {
    const response = await fetch('/api/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (response.status === 400) throw new Error('Wrong username or password.')
    if (!response.ok) throw new Error('Sign in failed. Try again later.')
    const data = await response.json()
    storeToken(data.token, setToken)
    await refreshMe(data.token)
  }

  async function signUp({ username, email, fullName, password, passwordConfirm }) {
    const response = await fetch('/api/auth/register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username,
        email,
        full_name: fullName,
        password,
        password_confirm: passwordConfirm,
      }),
    })
    if (response.status === 400) {
      const data = await response.json().catch(() => ({}))
      const first =
        data.username?.[0] ||
        data.email?.[0] ||
        data.password?.[0] ||
        data.password_confirm?.[0] ||
        data.non_field_errors?.[0] ||
        data.detail
      throw new Error(
        typeof first === 'string' ? first : 'Could not create that account.',
      )
    }
    if (!response.ok) throw new Error('Sign up failed. Try again later.')
    const data = await response.json()
    storeToken(data.token, setToken)
    await refreshMe(data.token)
  }

  async function requestContributorAccess(note = '') {
    if (!token) throw new Error('Sign in to request access.')
    const response = await fetch('/api/auth/request-contributor/', {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ note }),
    })
    if (response.status === 400) {
      const data = await response.json().catch(() => ({}))
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Could not submit that request.',
      )
    }
    if (!response.ok) throw new Error('Could not submit that request.')
    const created = await response.json()
    setMe((current) =>
      current
        ? { ...current, access_request: created }
        : { username: '', is_contributor: false, access_request: created },
    )
    return created
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
      setMe(null)
      setMeStatus('idle')
    }
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        me,
        meStatus,
        signIn,
        signUp,
        signOut,
        refreshMe,
        requestContributorAccess,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// The hook lives beside its provider; the cost is only a full reload when this file is edited.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
