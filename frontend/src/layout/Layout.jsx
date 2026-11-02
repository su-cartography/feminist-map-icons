import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import logo from '../assets/logo.png'

const navClass = ({ isActive }) =>
  isActive ? 'site-nav__link is-active' : 'site-nav__link'

export default function Layout() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

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
            <NavLink to="/gallery" className={navClass}>
              Search
            </NavLink>
            <NavLink to="/resources" className={navClass}>
              Resources
            </NavLink>
            <NavLink to="/contribute" className={navClass}>
              Contribute
            </NavLink>
          </nav>
        </div>
      </header>
      <main id="main" className="site-main">
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="site-footer__inner">
          <p>
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
