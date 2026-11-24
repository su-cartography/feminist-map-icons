import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../auth'
import IconUploadForm from '../components/IconUploadForm'
import PageHero from '../components/PageHero'

export default function ContributePage() {
  const { token, me, meStatus, requestContributorAccess, refreshMe } = useAuth()
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [justSent, setJustSent] = useState(false)

  // Signed-out visitors should land on the auth page first.
  if (!token) return <Navigate to="/sign-in" replace />

  const pending =
    me?.access_request?.status === 'pending' || justSent
  const isContributor = Boolean(me?.is_contributor)

  async function handleRequest(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await requestContributorAccess(note.trim())
      setJustSent(true)
      setNote('')
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the server.' : err.message,
      )
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRefresh() {
    setError('')
    setRefreshing(true)
    try {
      const data = await refreshMe()
      if (data?.is_contributor) setJustSent(false)
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the server.' : err.message,
      )
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <section className="contribute-page">
      <PageHero
        eyebrow="Contributor studio"
        title="Contribute"
        lead="Upload new map icons or request contributor access. New uploads start as pending until review."
      >
        {meStatus === 'ready' && me && (
          <p className="page-banner__chip">
            Signed in as <strong>{me.username}</strong>
            {isContributor ? ' · Contributor' : ''}
          </p>
        )}
      </PageHero>

      <div className="wrap contribute-page__body">
        {meStatus === 'loading' && (
          <p className="access-status">Checking your account…</p>
        )}

        {meStatus === 'error' && (
          <p className="access-status access-status--error" role="alert">
            Could not load your account status. Refresh and try again.
          </p>
        )}

        {meStatus === 'ready' && !isContributor && (
          <div className="access-panel">
            <h2>Contributor access required</h2>
            <p>
              You are signed in as <strong>{me.username}</strong>. Upload tools
              stay locked until a project admin grants the Contributor role in
              Django admin.
            </p>

            {pending ? (
              <div className="access-panel__confirm" role="status">
                <p>
                  Your request was sent and is <strong>pending approval</strong>.
                </p>
                <p>
                  You still cannot upload. After an admin grants access, use
                  Check access below to unlock the upload form.
                </p>
                {error && (
                  <p className="access-form__error" role="alert">
                    {error}
                  </p>
                )}
                <button
                  type="button"
                  className="btn"
                  onClick={handleRefresh}
                  disabled={refreshing}
                >
                  {refreshing ? 'Checking…' : 'Check access'}
                </button>
              </div>
            ) : (
              <form className="access-form" onSubmit={handleRequest}>
                <label htmlFor="access-note">Note for the team (optional)</label>
                <textarea
                  id="access-note"
                  name="note"
                  rows={3}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Why you’d like to contribute…"
                />
                {error && (
                  <p className="access-form__error" role="alert">
                    {error}
                  </p>
                )}
                <button type="submit" className="btn" disabled={submitting}>
                  {submitting ? 'Sending request…' : 'Request contributor access'}
                </button>
              </form>
            )}
          </div>
        )}

        {meStatus === 'ready' && isContributor && (
          <IconUploadForm token={token} username={me.username} />
        )}

        <p>
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </section>
  )
}
