import { ArrowLeft, Mail, ShieldCheck, Sparkles, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { authAPI, historyAPI } from '../utils/api'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [skinType, setSkinType] = useState('Loading...')

  useEffect(() => {
    let active = true
    authAPI.me().then(res => {
      if (!active) return
      const savedProfile = res.data.profile
      if (savedProfile.skin_type) setSkinType(`${savedProfile.skin_type} Skin`)
    }).catch(() => {})
    historyAPI.getAll()
      .then(res => {
        if (!active) return
        const latestScan = res.data.history?.[0]
        const condition = latestScan?.condition
        setSkinType(condition
          ? `${condition.charAt(0).toUpperCase()}${condition.slice(1)} Skin`
          : 'Not analyzed')
      })
      .catch(() => { if (active) setSkinType('Not analyzed') })
    return () => { active = false }
  }, [])

  return (
    <div className="profile-page">
      <div className="profile-header">
        <button className="profile-back" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={18} />
          <span>Back</span>
        </button>
        <div>
          <p className="dashboard-eyebrow">Your account</p>
          <h1>Profile</h1>
        </div>
      </div>

      <div className="profile-card">
        <div className="profile-hero">
          <div className="profile-avatar">{user?.name?.charAt(0)?.toUpperCase() || 'U'}</div>
          <div>
            <p className="profile-label">Personal information</p>
            <h2>{user?.name || 'Guest user'}</h2>
          </div>
        </div>

        <div className="profile-grid">
          <div className="profile-item">
            <div className="profile-icon"><UserRound size={18} /></div>
            <div>
              <span>Full name</span>
              <strong>{user?.name || 'Not available'}</strong>
            </div>
          </div>

          <div className="profile-item">
            <div className="profile-icon"><Mail size={18} /></div>
            <div>
              <span>Email address</span>
              <strong>{user?.email || 'Not available'}</strong>
            </div>
          </div>

          <div className="profile-item">
            <div className="profile-icon"><ShieldCheck size={18} /></div>
            <div>
              <span>Account status</span>
              <strong>Active</strong>
            </div>
          </div>

          <div className="profile-item">
            <div className="profile-icon"><Sparkles size={18} /></div>
            <div>
              <span>Skin profile</span>
              <strong>{skinType}</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="profile-actions">
        <button className="btn-primary" onClick={() => navigate('/dashboard')}>Back to dashboard</button>
        <button className="btn-ghost" onClick={() => { logout(); navigate('/') }}>Log out</button>
      </div>
    </div>
  )
}
