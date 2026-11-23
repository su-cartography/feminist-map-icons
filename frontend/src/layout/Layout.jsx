import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import logo from '../assets/logo.png'
import { useAuth } from '../auth'

const navClass = ({ isActive }) =>
  isActive ? 'site-nav__link is-active' : 'site-nav__link'

function scrollToGallery() {
  document.getElementById('gallery')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

export default function Layout() {
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { token, me, signOut } = useAuth()
  const [notice, setNotice] = useState('')
  const [chipReady, setChipReady] = useState(false)
  const signedInAs = me?.username

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Matches the toast-fade animation in App.css; clearing lets the next sign-out show it again.
  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(() => setNotice(''), 4000)
    return () => clearTimeout(timer)
  }, [notice])

  useEffect(() => {
    if (!token) {
      setChipReady(false)
      return
    }
    setChipReady(false)
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => setChipReady(true))
    })
    return () => cancelAnimationFrame(frame)
  }, [token, signedInAs])

  async function handleSignOut() {
    await signOut()
    navigate('/')
    setNotice('Signed out')
  }

  function handleSearchClick(event) {
    event.preventDefault()
    if (location.pathname === '/') {
      scrollToGallery()
      return
    }
    navigate({ pathname: '/', hash: 'gallery' })
  }

  return (
    <div className="site">
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <header className={scrolled ? 'site-header is-scrolled' : 'site-header'}>
        <div className="site-header__inner">
          <NavLink to="/" className="site-brand" end>
            <img src={logo} alt="" width={40} height={40} />
            <span>Gallery of Possibilities</span>
          </NavLink>
          <nav className="site-nav" aria-label="Main">
            <a
              href="/#gallery"
              className="site-nav__link"
              onClick={handleSearchClick}
            >
              Search
            </a>
            <NavLink to="/resources" className={navClass}>
              Resources
            </NavLink>
            {token ? (
              <NavLink to="/contribute" className={navClass}>
                Contribute
              </NavLink>
            ) : (
              <NavLink to="/sign-in" className={navClass}>
                Contribute
              </NavLink>
            )}
          </nav>

          {token ? (
            <div
              className={
                chipReady ? 'site-session is-ready' : 'site-session'
              }
            >
              <span className="site-session__glow" aria-hidden="true" />
              <span className="site-session__live" aria-hidden="true" />
              <div className="site-session__copy">
                <span className="site-session__label">Signed in as</span>
                <strong
                  className="site-session__name"
                  key={signedInAs || 'loading'}
                >
                  {signedInAs || '…'}
                </strong>
              </div>
              <button
                type="button"
                className="site-session__out"
                onClick={handleSignOut}
              >
                Sign out
              </button>
            </div>
          ) : (
            <NavLink to="/sign-in" className="site-session site-session--guest">
              Sign in
            </NavLink>
          )}
        </div>
      </header>
      <main id="main" className="site-main">
        <Outlet />
      </main>
      {notice && (
        <div className="toast" role="status">
          {notice}
        </div>
      )}
      <footer className="site-footer">
        <div className="site-footer__glow" aria-hidden="true" />
        <div className="site-footer__inner">
          <div className="site-footer__brand">
            <img src={logo} alt="" width={36} height={36} />
            <span>Gallery of Possibilities</span>
          </div>
          <p className="site-footer__contact">
            Contact:{' '}
            <a href="mailto:mkelly51@syr.edu">mkelly51@syr.edu</a>
          </p>
          <p className="site-footer__thanks">
            Funders and special thanks: NEH, OSPO, Sloan, FCAR
          </p>
        </div>
      </footer>
    </div>
  )
}
