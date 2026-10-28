import { NavLink } from 'react-router-dom'

const navigationItems = [
  { to: '/', label: 'main' },
  { to: '/search', label: 'search' },
  { to: '/friends', label: 'friends' },
]

export function AppNavigation() {
  return (
    <nav className="app-navigation" aria-label="Primary navigation">
      {navigationItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            isActive ? 'nav-link nav-link--active' : 'nav-link'
          }
        >
          <span className="nav-label">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
