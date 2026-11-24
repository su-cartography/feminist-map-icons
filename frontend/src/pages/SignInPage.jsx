import { useEffect, useId, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'
import PageHero from '../components/PageHero'

export default function SignInPage() {
  const { token, signIn, signUp } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const modeParam = searchParams.get('mode') === 'signup' ? 'signup' : 'signin'
  const [mode, setMode] = useState(modeParam)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [panelKey, setPanelKey] = useState(0)
  const formId = useId()

  useEffect(() => {
    setMode(modeParam)
  }, [modeParam])

  if (token) return <Navigate to="/contribute" replace />

  function switchMode(next) {
    if (next === mode) return
    setError('')
    setNotice('')
    setShowPassword(false)
    setShowConfirm(false)
    setMode(next)
    setPanelKey((key) => key + 1)
    setSearchParams(next === 'signup' ? { mode: 'signup' } : {}, { replace: true })
  }

  async function handleSignIn(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError('')
    setNotice('')
    setSubmitting(true)
    try {
      await signIn(form.get('username'), form.get('password'))
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the server.' : err.message,
      )
      setSubmitting(false)
    }
  }

  async function handleSignUp(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const password = form.get('password')
    const passwordConfirm = form.get('confirm_password')
    setError('')
    setNotice('')
    if (password !== passwordConfirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await signUp({
        username: form.get('username'),
        email: form.get('email'),
        fullName: form.get('full_name'),
        password,
        passwordConfirm,
      })
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the server.' : err.message,
      )
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page">
      <PageHero
        eyebrow="Gallery of Possibilities"
        title={mode === 'signin' ? 'Welcome back' : 'Join the gallery'}
        lead={
          mode === 'signin'
            ? 'Sign in with your account to contribute feminist map icons.'
            : 'Create an account first, then request contributor access. You can upload only after the team approves you.'
        }
      />

      <div className="wrap auth-shell">
        <div className="auth-card">
          <div
            className="auth-toggle"
            role="tablist"
            aria-label="Sign in or sign up"
          >
            <span
              className="auth-toggle__thumb"
              data-mode={mode}
              aria-hidden="true"
            />
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signin'}
              className={
                mode === 'signin'
                  ? 'auth-toggle__btn is-active'
                  : 'auth-toggle__btn'
              }
              onClick={() => switchMode('signin')}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
              className={
                mode === 'signup'
                  ? 'auth-toggle__btn is-active'
                  : 'auth-toggle__btn'
              }
              onClick={() => switchMode('signup')}
            >
              Sign up
            </button>
          </div>

          <div className="auth-panel" key={panelKey}>
            {mode === 'signin' ? (
              <form className="auth-form" onSubmit={handleSignIn}>
                <label htmlFor={`${formId}-username`}>Username</label>
                <input
                  id={`${formId}-username`}
                  name="username"
                  autoComplete="username"
                  required
                />

                <label htmlFor={`${formId}-password`}>Password</label>
                <div className="auth-field">
                  <input
                    id={`${formId}-password`}
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    className="auth-field__reveal"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>

                {error && (
                  <p className="auth-form__error" role="alert">
                    {error}
                  </p>
                )}

                <button type="submit" className="btn auth-form__submit" disabled={submitting}>
                  {submitting ? 'Signing in…' : 'Sign in'}
                </button>
              </form>
            ) : (
              <form className="auth-form" onSubmit={handleSignUp}>
                <label htmlFor={`${formId}-username-new`}>Username</label>
                <input
                  id={`${formId}-username-new`}
                  name="username"
                  autoComplete="username"
                  required
                />

                <label htmlFor={`${formId}-name`}>Full name</label>
                <input
                  id={`${formId}-name`}
                  name="full_name"
                  autoComplete="name"
                />

                <label htmlFor={`${formId}-email`}>Email</label>
                <input
                  id={`${formId}-email`}
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                />

                <label htmlFor={`${formId}-new-password`}>Password</label>
                <div className="auth-field">
                  <input
                    id={`${formId}-new-password`}
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    className="auth-field__reveal"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>

                <label htmlFor={`${formId}-confirm`}>Confirm password</label>
                <div className="auth-field">
                  <input
                    id={`${formId}-confirm`}
                    name="confirm_password"
                    type={showConfirm ? 'text' : 'password'}
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    className="auth-field__reveal"
                    aria-label={
                      showConfirm ? 'Hide confirm password' : 'Show confirm password'
                    }
                    onClick={() => setShowConfirm((value) => !value)}
                  >
                    {showConfirm ? 'Hide' : 'Show'}
                  </button>
                </div>

                {error && (
                  <p className="auth-form__error" role="alert">
                    {error}
                  </p>
                )}
                {notice && (
                  <p className="auth-form__notice" role="status">
                    {notice}
                  </p>
                )}

                <button
                  type="submit"
                  className="btn auth-form__submit"
                  disabled={submitting}
                >
                  {submitting ? 'Creating account…' : 'Create account'}
                </button>
                <p className="auth-form__hint">
                  Creating an account does not grant upload rights. After you
                  sign up, request contributor access and wait for admin
                  approval.
                </p>
              </form>
            )}
          </div>

          <div className="auth-divider">
            <span>or continue with</span>
          </div>

          <button
            type="button"
            className="auth-google"
            disabled
            title="Google sign-in comes in a later issue"
          >
            <svg
              className="auth-google__icon"
              viewBox="0 0 24 24"
              width="18"
              height="18"
              aria-hidden="true"
            >
              <path
                fill="#EA4335"
                d="M12 10.2v3.6h5.1c-.2 1.2-.9 2.2-1.9 2.9l3.1 2.4c1.8-1.7 2.9-4.1 2.9-7 0-.7-.1-1.3-.2-1.9H12z"
              />
              <path
                fill="#34A853"
                d="M5.3 14.3 4.4 15l-2.7 2.1C3.5 20.5 7.4 23 12 23c3 0 5.5-1 7.3-2.7l-3.1-2.4c-.9.6-2 .9-3.2.9-2.5 0-4.6-1.7-5.3-4z"
              />
              <path
                fill="#4A90E2"
                d="M3.2 6.9A10.9 10.9 0 0 0 1 12c0 1.8.4 3.4 1.2 4.9l3.1-2.4A6.5 6.5 0 0 1 5.5 12c0-.9.2-1.8.5-2.6z"
              />
              <path
                fill="#FBBC05"
                d="M12 4.8c1.7 0 3.2.6 4.3 1.7l3.2-3.2C17.5 1.4 15 0 12 0 7.4 0 3.5 2.5 1.7 6.1l3.1 2.4C5.5 6.5 7.6 4.8 12 4.8z"
              />
            </svg>
            Google (soon)
          </button>

          <p className="auth-card__footer">
            {mode === 'signin' ? (
              <>
                Need an account?{' '}
                <button
                  type="button"
                  className="auth-card__link"
                  onClick={() => switchMode('signup')}
                >
                  Sign up
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  className="auth-card__link"
                  onClick={() => switchMode('signin')}
                >
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </section>
  )
}
