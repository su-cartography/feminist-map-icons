import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import PageHero from '../components/PageHero'

const PAGE_SIZE = 50

const STATUS_META = {
  draft: { label: 'Draft', tone: 'draft' },
  pending: { label: 'Pending', tone: 'pending' },
  changes_requested: { label: 'Changes requested', tone: 'changes' },
  approved: { label: 'Approved', tone: 'approved' },
  rejected: { label: 'Rejected', tone: 'rejected' },
  published: { label: 'Published', tone: 'published' },
}

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'pending', label: 'Pending' },
  { id: 'changes_requested', label: 'Changes' },
  { id: 'approved', label: 'Approved' },
  { id: 'published', label: 'Published' },
  { id: 'rejected', label: 'Rejected' },
]

function statusMeta(status) {
  return STATUS_META[status] || { label: status || 'Unknown', tone: 'draft' }
}

function AuthThumb({ uniqueId, token, label }) {
  const [src, setSrc] = useState('')

  useEffect(() => {
    if (!uniqueId || !token) {
      setSrc('')
      return undefined
    }

    const controller = new AbortController()
    let objectUrl = ''
    let cancelled = false

    async function loadPreview() {
      // Hit the gated file routes through the Vite proxy with the token.
      // Absolute serializer URLs (port 8000) fail as <img>/cross-origin fetches.
      for (const kind of ['png', 'svg']) {
        const response = await fetch(
          `/api/icons/${encodeURIComponent(uniqueId)}/${kind}/`,
          {
            headers: { Authorization: `Token ${token}` },
            signal: controller.signal,
          },
        )
        if (!response.ok) continue
        const blob = await response.blob()
        if (cancelled || !blob || blob.size === 0) return
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
        return
      }
    }

    loadPreview().catch(() => {})

    return () => {
      cancelled = true
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [uniqueId, token])

  if (!src) {
    return <span className="subs-card__fallback">{label}</span>
  }
  return <img src={src} alt="" loading="lazy" />
}

export default function MySubmissionsPage() {
  const { token, me, meStatus } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('all')
  const [state, setState] = useState({
    status: 'loading',
    icons: [],
    count: 0,
  })

  useEffect(() => {
    if (!token) return undefined

    const controller = new AbortController()
    setState((current) => ({ ...current, status: 'loading' }))

    const params = new URLSearchParams({ mine: '1', page: String(page) })
    fetch(`/api/icons/?${params}`, {
      headers: { Authorization: `Token ${token}` },
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load submissions')
        return response.json()
      })
      .then((data) => {
        setState({
          status: 'ready',
          icons: data.results || [],
          count: data.count || 0,
        })
      })
      .catch((error) => {
        if (error.name === 'AbortError') return
        setState((current) => ({ ...current, status: 'error', icons: [] }))
      })

    return () => controller.abort()
  }, [token, page])

  const counts = useMemo(() => {
    const tallies = {
      all: state.icons.length,
      pending: 0,
      changes_requested: 0,
      approved: 0,
      published: 0,
      rejected: 0,
      draft: 0,
    }
    for (const icon of state.icons) {
      if (tallies[icon.status] != null) tallies[icon.status] += 1
    }
    return tallies
  }, [state.icons])

  const visibleIcons = useMemo(() => {
    if (filter === 'all') return state.icons
    return state.icons.filter((icon) => icon.status === filter)
  }, [state.icons, filter])

  if (!token) return <Navigate to="/sign-in" replace />

  const totalPages = Math.max(1, Math.ceil(state.count / PAGE_SIZE))

  function openIcon(uniqueId) {
    navigate(`/icons/${uniqueId}`, {
      state: { backgroundLocation: location },
    })
  }

  return (
    <section className="subs-page">
      <PageHero
        eyebrow="Your studio shelf"
        title="My submissions"
        lead="Track every icon you have sent in — from first upload to published in the gallery."
      >
        {meStatus === 'ready' && me && (
          <p className="page-banner__chip">
            Signed in as <strong>{me.username}</strong>
          </p>
        )}
      </PageHero>

      <div className="wrap subs-body">
        {meStatus === 'ready' && me && !me.is_contributor && (
          <p className="subs-note" role="status">
            Contributor access is still locked. Request it on{' '}
            <Link to="/contribute">Contribute</Link> before you can upload.
          </p>
        )}

        {state.status === 'ready' && state.icons.length > 0 && (
          <div className="subs-stats" aria-label="Submission counts">
            <div className="subs-stat">
              <span className="subs-stat__value">{state.count}</span>
              <span className="subs-stat__label">Total</span>
            </div>
            <div className="subs-stat is-pending">
              <span className="subs-stat__value">{counts.pending}</span>
              <span className="subs-stat__label">Pending</span>
            </div>
            <div className="subs-stat is-published">
              <span className="subs-stat__value">{counts.published}</span>
              <span className="subs-stat__label">Published</span>
            </div>
            <div className="subs-stat is-changes">
              <span className="subs-stat__value">
                {counts.changes_requested}
              </span>
              <span className="subs-stat__label">Changes</span>
            </div>
          </div>
        )}

        {state.status === 'ready' && state.icons.length > 0 && (
          <div className="subs-filters" role="tablist" aria-label="Filter by status">
            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={filter === item.id}
                className={
                  filter === item.id
                    ? 'subs-filter is-active'
                    : 'subs-filter'
                }
                onClick={() => setFilter(item.id)}
              >
                {item.label}
                <span>{item.id === 'all' ? state.icons.length : counts[item.id] || 0}</span>
              </button>
            ))}
          </div>
        )}

        {state.status === 'loading' && (
          <p className="subs-status">Loading your submissions…</p>
        )}

        {state.status === 'error' && (
          <p className="subs-status is-error" role="alert">
            Could not load your submissions. Refresh and try again.
          </p>
        )}

        {state.status === 'ready' && state.icons.length === 0 && (
          <div className="subs-empty" role="status">
            <div className="subs-empty__visual" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <h2>No submissions yet</h2>
            <p>
              Your shelf is empty. Upload an icon and it will land here with its
              review status.
            </p>
            <Link className="btn btn-yellow" to="/contribute">
              Upload an icon
            </Link>
          </div>
        )}

        {state.status === 'ready' &&
          state.icons.length > 0 &&
          visibleIcons.length === 0 && (
            <div className="subs-empty is-filter" role="status">
              <h2>Nothing in this lane</h2>
              <p>No submissions match that status filter right now.</p>
              <button
                type="button"
                className="btn"
                onClick={() => setFilter('all')}
              >
                Show all
              </button>
            </div>
          )}

        {state.status === 'ready' && visibleIcons.length > 0 && (
          <ul className="subs-grid">
            {visibleIcons.map((icon, index) => {
              const meta = statusMeta(icon.status)
              return (
                <li
                  key={icon.unique_id}
                  style={{ '--i': index }}
                  className="subs-grid__item"
                >
                  <button
                    type="button"
                    className="subs-card"
                    onClick={() => openIcon(icon.unique_id)}
                  >
                    <span className="subs-card__shine" aria-hidden="true" />
                    <span className="subs-card__preview">
                      <AuthThumb
                        uniqueId={icon.unique_id}
                        token={token}
                        label={icon.unique_id.slice(0, 2)}
                      />
                    </span>
                    <span className="subs-card__body">
                      <strong>{icon.primary_tag || icon.unique_id}</strong>
                      <span className="subs-card__meta">
                        <code>{icon.unique_id}</code>
                        {icon.designer ? ` · ${icon.designer}` : ''}
                      </span>
                      {icon.icon_description && (
                        <span className="subs-card__blurb">
                          {icon.icon_description}
                        </span>
                      )}
                    </span>
                    <span className={`subs-card__status is-${meta.tone}`}>
                      <span className="subs-card__pulse" aria-hidden="true" />
                      {meta.label}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}

        {state.status === 'ready' && state.count > PAGE_SIZE && (
          <div className="subs-pager">
            <button
              type="button"
              className="btn"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              className="btn"
              disabled={page >= totalPages}
              onClick={() =>
                setPage((current) => Math.min(totalPages, current + 1))
              }
            >
              Next
            </button>
          </div>
        )}

        <div className="subs-footer-links">
          <Link to="/contribute">← Upload another</Link>
          <Link to="/">Browse gallery</Link>
        </div>
      </div>
    </section>
  )
}
