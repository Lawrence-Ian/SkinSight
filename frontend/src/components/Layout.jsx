// src/components/Layout.jsx
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { BookOpen, ClipboardCheck, Home, MapPin, MessageCircle, ScanFace, Sparkles, UserRound } from 'lucide-react'

const NAV = [
  { key: 'home', to: '/dashboard', icon: Home, label: 'Home' },
  { key: 'scan', to: '/analysis', icon: ScanFace, label: 'Skin Analysis' },
  { key: 'routine', to: '/routine', icon: ClipboardCheck, label: 'Routine' },
  { key: 'map', to: '/map', icon: MapPin, label: 'Nearby Care' },
  { key: 'history', to: '/history', icon: BookOpen, label: 'History' },
]

const MOBILE_NAV = [
  { key: 'home', to: '/dashboard', icon: Home, label: 'Home', ariaLabel: 'Home' },
  { key: 'scan', to: '/analysis', icon: ScanFace, label: 'Scan', ariaLabel: 'Skin Analysis' },
  { key: 'routine', to: '/routine', icon: ClipboardCheck, label: 'Routine', ariaLabel: 'Routine' },
  { key: 'map', to: '/map', icon: MapPin, label: 'Care', ariaLabel: 'Nearby Care' },
  { key: 'history', to: '/history', icon: BookOpen, label: 'History', ariaLabel: 'History' },
  { key: 'chat', to: '/chat', icon: MessageCircle, label: 'Chat', ariaLabel: 'AI Chat' },
  { key: 'profile', to: '/profile', icon: UserRound, label: 'Profile', ariaLabel: 'Profile' },
]

const getActiveNavKey = ({ pathname, search }) => {
  if (pathname === '/dashboard' && search === '') return 'home'
  if (pathname === '/analysis') return 'scan'
  if (pathname === '/routine') return 'routine'
  if (pathname === '/map') return 'map'
  if (pathname === '/history') return 'history'
  if (pathname === '/chat') return 'chat'
  if (pathname === '/profile') return 'profile'
  return null
}

const getNavClickHandler = (key, navigate) => event => {
  if (key !== 'home' && key !== 'scan') return
  event.preventDefault()
  navigate(key === 'scan' ? '/analysis' : '/dashboard')
}

export default function Layout({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const activeNavKey = getActiveNavKey(location)

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar-brand"><span className="app-sidebar-mark"><Sparkles /></span><div><strong>SKINSIGHT</strong><small>AI Skin Analysis</small></div></div>
        <nav className="app-sidebar-nav">{NAV.map(({ key, to, icon: Icon, label }) => {
          const active = activeNavKey === key
          return <NavLink key={key} to={to} end onClick={getNavClickHandler(key, navigate)} className={`app-sidebar-link ${active ? 'active' : ''}`}><Icon size={19} /><span>{label}</span></NavLink>
        })}</nav>
        <div className="app-sidebar-bottom"><button className={`app-sidebar-link ${location.pathname === '/profile' ? 'active' : ''}`} onClick={() => navigate('/profile')}><UserRound size={19} /><span>Profile</span></button><button className={`app-sidebar-link ${location.pathname === '/chat' ? 'active' : ''}`} onClick={() => navigate('/chat')}><MessageCircle size={19} /><span>AI Chat</span></button></div>
      </aside>
      <div className="app-main-column">
        <header className="app-topbar">
          <div className="app-mobile-brand"><span className="app-sidebar-mark"><Sparkles /></span><strong>SKINSIGHT</strong></div>
        </header>
        <main className="app-content">{children}</main>
        <nav className="app-mobile-nav" aria-label="Primary navigation">
          {MOBILE_NAV.map(({ key, to, icon: Icon, label, ariaLabel }) => {
            const active = activeNavKey === key
            return <NavLink key={key} to={to} end onClick={getNavClickHandler(key, navigate)} aria-label={ariaLabel} aria-current={active ? 'page' : undefined} className={`app-mobile-nav-link ${active ? 'active' : ''}`}><Icon size={18} /><span>{label}</span></NavLink>
          })}
        </nav>
      </div>
    </div>
  )
}
