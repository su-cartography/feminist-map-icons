import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import logo from '../assets/logo.png'
import qgisPreview from '../assets/qgis-preview.png'

const ABOUT_CARDS = [
  {
    title: 'Configuration',
    body: 'Map icons and metadata are stored openly and served through this library’s API for the website and QGIS plugin.',
  },
  {
    title: 'Download and Install',
    body: 'Install the plugin from the QGIS Plugin Repository, or manually with zip files available on GitHub.',
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

function scrollToGallery() {
  document.getElementById('gallery')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

export default function HomePage() {
  const location = useLocation()
  const [previewIcons, setPreviewIcons] = useState([])
  const [previewStatus, setPreviewStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false

    async function loadPreview() {
      try {
        const response = await fetch('/api/icons/?page=1')
        if (!response.ok) throw new Error('Failed to load icons')
        const data = await response.json()
        const rows = Array.isArray(data) ? data : data.results || []
        if (!cancelled) {
          setPreviewIcons(rows.slice(0, 8))
          setPreviewStatus(rows.length ? 'ready' : 'empty')
        }
      } catch {
        if (!cancelled) setPreviewStatus('error')
      }
    }

    loadPreview()
    return () => {
      cancelled = true
    }
  }, [])

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

      <section className="intro-band">
        <div className="wrap intro-band__inner">
          <img src={logo} alt="" width={56} height={56} />
          <div>
            <h2>Gallery of Possibilities</h2>
            <p>
              The galleryofpossibilities is a feminist mapping tool and an
              alternative map icon library, grounded in feminist thought and
              practice that can be integrated into QGIS, an open-source mapping
              platform, and cartography more broadly.
            </p>
            <a
              className="btn"
              href="#gallery"
              onClick={(event) => {
                event.preventDefault()
                scrollToGallery()
              }}
            >
              Search icons
            </a>
          </div>
        </div>
      </section>

      <section
        id="gallery"
        className="home-gallery wrap"
        aria-labelledby="home-gallery-heading"
      >
        <h2 id="home-gallery-heading">Browse the library</h2>
        <p>
          Published icons from the API. Use Search in the header to jump back
          here anytime.
        </p>
        {previewStatus === 'loading' && (
          <p className="home-gallery__status">Loading icons…</p>
        )}
        {previewStatus === 'error' && (
          <p className="home-gallery__status">
            Icons will appear here when the API is running. Start the Django
            server, then refresh.
          </p>
        )}
        {previewStatus === 'empty' && (
          <p className="home-gallery__status">
            No published icons yet. Import icons on the backend to populate this
            gallery.
          </p>
        )}
        {previewStatus === 'ready' && (
          <ul className="icon-grid">
            {previewIcons.map((icon) => (
              <li key={icon.unique_id}>
                <Link
                  className="icon-card"
                  to={`/icons/${icon.unique_id}`}
                >
                  {icon.png_file ? (
                    <img
                      src={icon.png_file}
                      alt={icon.primary_tag || icon.unique_id}
                    />
                  ) : (
                    <span className="icon-card__fallback">
                      {icon.primary_tag || icon.unique_id}
                    </span>
                  )}
                  <span className="icon-card__label">
                    {icon.primary_tag || icon.unique_id}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
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
