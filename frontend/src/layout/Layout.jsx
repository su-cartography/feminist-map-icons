import { NavLink, Outlet } from 'react-router-dom'

const navClass = ({ isActive }) =>
  isActive ? 'site-nav__link is-active' : 'site-nav__link'

export default function Layout() {
  return (
    <div className="site">
      <header className="site-header">
        <div className="site-header__inner">
          <NavLink to="/" className="site-brand">
            Gallery of Possibilities
          </NavLink>
          <nav className="site-nav" aria-label="Main">
            <NavLink to="/" end className={navClass}>
              Home
            </NavLink>
            <NavLink to="/gallery" className={navClass}>
              Gallery
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="site-main">
        <Outlet />
      </main>
    </div>
  )
}
