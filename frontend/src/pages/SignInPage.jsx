import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function SignInPage() {
  const { token, signIn } = useAuth()
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Covers both a fresh sign-in and visiting this page while already signed in.
  if (token) return <Navigate to="/contribute" replace />

  async function handleSubmit(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError('')
    setSubmitting(true)
    try {
      await signIn(form.get('username'), form.get('password'))
    } catch (err) {
      // fetch rejects with a TypeError when the API can't be reached at all.
      setError(
        err instanceof TypeError ? 'Could not reach the server.' : err.message,
      )
      setSubmitting(false)
    }
  }

  return (
    <section className="page wrap">
      <h1>Sign in</h1>
      <p>Contributors sign in here to upload icons.</p>
      <form className="sign-in" onSubmit={handleSubmit}>
        <label htmlFor="username">Username</label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
        {error && (
          <p className="sign-in__error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}
