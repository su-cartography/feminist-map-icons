import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { saveFile } from '../utils/download'

const META_FIELDS = [
  ['designer', 'Designer'],
  ['metadata_source', 'Metadata Source'],
  ['uploader', 'Uploader'],
  ['primary_tag', 'Primary Tag'],
  ['secondary_tags', 'Secondary Tags'],
  ['when_created', 'When Created'],
  ['when_uploaded', 'When Uploaded'],
  ['where_created', 'Where Created'],
  ['icon_geography', 'Icon Geography'],
  ['icon_description', 'Icon Description'],
  ['icon_context', 'Icon Context'],
  ['creation_context', 'Creation Context'],
  ['notes', 'Notes'],
]

function metaValue(icon, key) {
  if (key === 'secondary_tags') {
    const names = (icon.tags || []).map((tag) => tag.name).filter(Boolean)
    return names.length ? names.join(', ') : ''
  }
  const value = icon[key]
  return value == null ? '' : String(value).trim()
}

export default function IconDetailPage() {
  const { uniqueId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const titleId = useId()
  const menuId = useId()
  const closingRef = useRef(false)

  const gallerySearch = location.state?.gallerySearch || ''
  const background = location.state?.backgroundLocation

  const [isOpen, setIsOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [status, setStatus] = useState('loading')
  const [icon, setIcon] = useState(null)
  const [downloading, setDownloading] = useState(null)

  const closeMini = useCallback(() => {
    if (closingRef.current) return
    closingRef.current = true
    setMenuOpen(false)
    setIsOpen(false)
    window.setTimeout(() => {
      if (background) {
        navigate(
          `${background.pathname}${background.search}${background.hash || ''}`,
          { replace: true },
        )
        return
      }
      navigate(
        { pathname: '/', search: gallerySearch, hash: 'gallery' },
        { replace: true },
      )
    }, 250)
  }, [background, gallerySearch, navigate])

  useEffect(() => {
    closingRef.current = false
    setIsOpen(false)
    document.body.classList.add('mini-open')
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => setIsOpen(true))
    })
    return () => {
      cancelAnimationFrame(frame)
      document.body.classList.remove('mini-open')
    }
  }, [uniqueId])

  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    setIcon(null)
    setMenuOpen(false)

    fetch(`/api/icons/${encodeURIComponent(uniqueId)}/`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.status === 404) {
          setStatus('missing')
          return
        }
        if (!response.ok) throw new Error('Failed to load icon')
        setIcon(await response.json())
        setStatus('ready')
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        setStatus('error')
      })

    return () => controller.abort()
  }, [uniqueId])

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key !== 'Escape') return
      if (menuOpen) {
        setMenuOpen(false)
        return
      }
      closeMini()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [menuOpen, closeMini])

  useEffect(() => {
    if (!menuOpen) return
    function onDocClick() {
      setMenuOpen(false)
    }
    document.addEventListener('click', onDocClick)
    return () => document.removeEventListener('click', onDocClick)
  }, [menuOpen])

  function toggleMenu(event) {
    event.stopPropagation()
    setMenuOpen((open) => !open)
  }

  async function downloadKind(kind, event) {
    event.stopPropagation()
    if (!icon) return

    const url = kind === 'png' ? icon.png_file : icon.svg_file
    const filename = `${icon.unique_id}.${kind}`

    if (!url) {
      alert(`This icon has no ${kind.toUpperCase()} file.`)
      return
    }

    // Fetch as a blob so PNG (served inline for <img>) still saves locally,
    // instead of the browser navigating to the API image URL.
    setDownloading(kind)
    try {
      const response = await fetch(url)
      if (!response.ok) throw new Error('download failed')
      const blob = await response.blob()
      await saveFile(blob, filename)
    } catch (err) {
      console.error(err)
      alert(`Could not download that ${kind.toUpperCase()}.`)
    } finally {
      setDownloading(null)
      setMenuOpen(false)
    }
  }

  const title =
    (icon && (icon.primary_tag || icon.unique_id)) || 'Icon details'
  const previewSrc = icon?.png_file || icon?.svg_file || ''

  return (
    <div className={isOpen ? 'mini is-open' : 'mini'} role="presentation">
      <div
        className="mini-backdrop"
        onClick={closeMini}
        aria-hidden="true"
      />
      <div
        className="mini-page"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <button
          type="button"
          className="detail-close"
          aria-label="Close details"
          onClick={closeMini}
        >
          ×
        </button>

        <h2 id={titleId}>{status === 'ready' ? title : 'Icon details'}</h2>

        {status === 'loading' && <p className="mini-status">Loading icon…</p>}
        {status === 'missing' && (
          <p className="mini-status">This icon was not found.</p>
        )}
        {status === 'error' && (
          <p className="mini-status mini-status--error">
            Icon details could not be loaded. Is the API running?
          </p>
        )}

        {status === 'ready' && icon && (
          <>
            <div className="mini-visual">
              <div className="detail-preview-frame">
                {previewSrc ? (
                  <img
                    className="detail-preview"
                    src={previewSrc}
                    alt={title}
                  />
                ) : (
                  <span className="detail-preview detail-preview--empty" />
                )}
              </div>

              <div className="mini-dl" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  className="mini-dl-toggle"
                  aria-expanded={menuOpen ? 'true' : 'false'}
                  aria-haspopup="menu"
                  aria-controls={menuId}
                  onClick={toggleMenu}
                >
                  <svg
                    className="mini-dl-icon"
                    viewBox="0 0 24 24"
                    width="18"
                    height="18"
                    aria-hidden="true"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M12 3v12" />
                    <path d="m7 10 5 5 5-5" />
                    <path d="M5 21h14" />
                  </svg>
                  <span>Download</span>
                  <svg
                    className="mini-dl-caret"
                    viewBox="0 0 24 24"
                    width="14"
                    height="14"
                    aria-hidden="true"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </button>

                <div
                  id={menuId}
                  className="mini-dl-menu"
                  role="menu"
                  hidden={!menuOpen}
                >
                  <button
                    type="button"
                    className="mini-dl-option"
                    role="menuitem"
                    data-kind="png"
                    disabled={!icon.png_file || downloading === 'png'}
                    onClick={(event) => downloadKind('png', event)}
                  >
                    {downloading === 'png' ? 'Loading…' : '…as PNG'}
                  </button>
                  <button
                    type="button"
                    className="mini-dl-option"
                    role="menuitem"
                    data-kind="svg"
                    disabled={!icon.svg_file || downloading === 'svg'}
                    onClick={(event) => downloadKind('svg', event)}
                  >
                    {downloading === 'svg' ? 'Loading…' : '…as SVG'}
                  </button>
                </div>
              </div>
            </div>

            <h3 className="mini-meta-heading">Metadata</h3>
            <dl className="detail-meta detail-meta--refined">
              {META_FIELDS.map(([key, label], index) => (
                <div key={key} style={{ '--m': index }}>
                  <dt>{label}</dt>
                  <dd>{metaValue(icon, key) || '—'}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </div>
    </div>
  )
}
