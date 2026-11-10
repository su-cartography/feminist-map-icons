import { useCallback, useEffect, useState } from 'react'
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from 'react-router-dom'
import logo from '../assets/logo.png'
import qgisPreview from '../assets/qgis-preview.png'

const ABOUT_CARDS = [
  {
    title: 'Configuration',
    body: 'Map icons and metadata are stored openly and served through this library’s API for the website and QGIS plugin.',
  },
  {
    title: 'Download and Install',
    body: (
      <>
        Install the plugin from the{' '}
        <a
          href="https://plugins.qgis.org/plugins/galleryofpossibilities/"
          target="_blank"
          rel="noopener noreferrer"
        >
          QGIS Plugin Repository
        </a>
        , or manually with zip files available on GitHub.
      </>
    ),
  },
  {
    title: 'File Formats',
    body: 'Map icons are served as PNG images and digitized SVGs.',
  },
  {
    title: 'Search and Apply',
    body: 'Filter by tags, place names, designers, and organizations and apply icons to your map.',
  },
  {
    title: 'Style and Symbolize',
    body: 'Customize by adding color and stroke to SVGs and backgrounds for added contrast.',
  },
  {
    title: 'Favorites',
    body: 'Curate and save a custom subset of map icons for a particular use case.',
  },
]

// Matches REST_FRAMEWORK PAGE_SIZE in backend settings.
const PAGE_SIZE = 50

function scrollToGallery() {
  document.getElementById('gallery')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

export default function HomePage() {
  const location = useLocation()
  const navigate = useNavigate()
  // The URL is the source of truth for the search, so a back link or a
  // shared link lands on the same results.
  const [searchParams] = useSearchParams()
  const q = searchParams.get('q') || ''
  const page = Number(searchParams.get('page')) || 1
  const searchKey = `${q}|${page}`

  const [query, setQuery] = useState(q)
  const [syncedQ, setSyncedQ] = useState(q)
  if (q !== syncedQ) {
    // The URL changed under us (browser back/forward): refill the box,
    // unless it already says the same thing modulo whitespace.
    setSyncedQ(q)
    if (query.trim() !== q) setQuery(q)
  }

  const [gallery, setGallery] = useState({
    for: null,
    status: 'loading',
    icons: [],
    count: 0,
    next: null,
    previous: null,
  })
  const [format, setFormat] = useState('png')

  const showSearch = useCallback(
    (nextQ, nextPage, options) => {
      const params = new URLSearchParams()
      if (nextQ) params.set('q', nextQ)
      if (nextPage > 1) params.set('page', nextPage)
      navigate({ search: params.toString(), hash: '#gallery' }, options)
    },
    [navigate],
  )

  useEffect(() => {
    // Debounce typing; a new query always starts at page 1. Replace rather
    // than push so each keystroke pause isn't its own history entry.
    const trimmed = query.trim()
    if (trimmed === q) return
    const timer = window.setTimeout(() => {
      showSearch(trimmed, 1, { replace: true })
    }, 300)
    return () => window.clearTimeout(timer)
  }, [query, q, showSearch])

  useEffect(() => {
    // Aborting on every change keeps a slow earlier response from
    // overwriting a newer one, and also covers unmount.
    const controller = new AbortController()
    const params = new URLSearchParams({ page })
    if (q) params.set('q', q)

    fetch(`/api/icons/?${params}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load icons')
        return response.json()
      })
      .then((data) => {
        setGallery({
          for: searchKey,
          status: 'ready',
          icons: data.results,
          count: data.count,
          next: data.next,
          previous: data.previous,
        })
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setGallery((current) => ({
            ...current,
            for: searchKey,
            status: 'error',
          }))
        }
      })

    return () => controller.abort()
  }, [q, page, searchKey])

  // Until the response for the current search lands, keep showing the old
  // grid under a loading line.
  const status = gallery.for === searchKey ? gallery.status : 'loading'

  function goToPage(nextPage) {
    showSearch(q, nextPage)
    scrollToGallery()
  }

  useEffect(() => {
    if (location.hash === '#gallery') {
      // Wait a tick so layout/images can settle before scrolling.
      const timer = window.setTimeout(scrollToGallery, 50)
      return () => window.clearTimeout(timer)
    }
  }, [location.hash])

  return (
    <div className="home">
      <section className="hero wrap">
        <img className="hero__logo" src={logo} alt="" width={72} height={72} />
        <h1>
          Gallery of <em>Possibilities</em>
        </h1>
        <p className="hero__tagline">
          A feminist map icon gallery and QGIS plugin.
        </p>
        <div className="actions">
          <a className="btn btn-yellow" href="#gallery" onClick={(event) => {
            event.preventDefault()
            scrollToGallery()
          }}>
            Search
          </a>
          <a
            className="btn"
            href="https://plugins.qgis.org/plugins/galleryofpossibilities/"
            target="_blank"
            rel="noopener noreferrer"
          >
            QGIS Plugin
          </a>
          <Link className="btn" to="/resources">
            Resources
          </Link>
          <Link className="btn" to="/contribute">
            Contribute
          </Link>
        </div>
        <img
          className="preview"
          src={qgisPreview}
          alt="QGIS map using Gallery of Possibilities icons"
        />
      </section>

      <section
        id="gallery"
        className="gallery"
        aria-labelledby="home-gallery-heading"
      >
        <div className="wrap gallery__inner">
          <img
            className="gallery__logo"
            src={logo}
            alt=""
            width={80}
            height={80}
          />
          <h2 id="home-gallery-heading">Gallery of Possibilities</h2>
          <p className="gallery__intro">
            The <i>galleryofpossibilities</i> is a feminist mapping tool and an
            alternative map icon library, grounded in feminist thought and
            practice that can be integrated into QGIS, an open-source mapping
            platform, and cartography more broadly.
          </p>

          <div className="search-field" role="search">
            <label className="sr-only" htmlFor="gallery-search">
              Search icons by tags, geography, or designer
            </label>
            <svg className="search-icon" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input
              id="gallery-search"
              className="gallery-search"
              type="search"
              placeholder="Search by tags, geography, or designer…"
              autoComplete="off"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          <div className="grid-toolbar">
            <p className="format-mode">
              {format === 'svg' ? 'Showing SVGs' : 'Showing PNGs'}
            </p>
            <button
              type="button"
              className={
                format === 'svg' ? 'rainbow-toggle is-svg' : 'rainbow-toggle'
              }
              aria-pressed={format === 'svg'}
              title="Switch between PNG and SVG"
              aria-label="Switch between PNG and SVG icons"
              onClick={() =>
                setFormat((current) => (current === 'png' ? 'svg' : 'png'))
              }
            >
              <span className="sr-only">Toggle PNG / SVG</span>
            </button>
          </div>

          <p className="home-gallery__status" aria-live="polite">
            {status === 'loading' && 'Loading icons…'}
            {status === 'error' &&
              'Icons could not be loaded. Is the API running?'}
            {status === 'ready' &&
              gallery.count === 0 &&
              (q
                ? `No icons match “${q}”.`
                : 'No published icons yet.')}
            {status === 'ready' &&
              gallery.count > 0 &&
              `Showing ${(page - 1) * PAGE_SIZE + 1}–${
                (page - 1) * PAGE_SIZE + gallery.icons.length
              } of ${gallery.count} icons`}
          </p>

          {gallery.icons.length > 0 && (
            <ul className="icon-grid">
              {gallery.icons.map((icon, index) => {
                const label = icon.primary_tag || icon.unique_id
                const src =
                  format === 'svg' && icon.svg_file
                    ? icon.svg_file
                    : icon.png_file
                return (
                  <li key={icon.unique_id} style={{ '--i': index }}>
                    <Link
                      className="icon-card"
                      to={`/icons/${icon.unique_id}`}
                      state={{
                        backgroundLocation: location,
                        gallerySearch: location.search,
                      }}
                    >
                      {src ? (
                        <img src={src} alt="" loading="lazy" />
                      ) : (
                        <span className="icon-card__fallback" aria-hidden="true" />
                      )}
                      <span className="icon-card__label">{label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}

          {(gallery.previous || gallery.next) && (
            <nav className="pager" aria-label="Gallery pages">
              <button
                type="button"
                className="btn"
                disabled={!gallery.previous}
                onClick={() => goToPage(page - 1)}
              >
                ← Previous
              </button>
              <span>
                Page {page} of {Math.ceil(gallery.count / PAGE_SIZE)}
              </span>
              <button
                type="button"
                className="btn"
                disabled={!gallery.next}
                onClick={() => goToPage(page + 1)}
              >
                Next →
              </button>
            </nav>
          )}
        </div>
      </section>

      <section className="about wrap" aria-labelledby="about-heading">
        <h2 id="about-heading">About the galleryofpossibilities</h2>
        <ul className="about-grid">
          {ABOUT_CARDS.map((card) => (
            <li key={card.title} className="about-card">
              <h3>{card.title}</h3>
              <p>{card.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="contribute-teaser wrap">
        <h2>Contribute</h2>
        <p>Contribute feminist map icons to the gallery.</p>
        <Link className="btn" to="/contribute">
          Contribute
        </Link>
      </section>
    </div>
  )
}
