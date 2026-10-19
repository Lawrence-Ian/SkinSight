// src/pages/AuthPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, ArrowLeft, Sparkles } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { authAPI } from '../utils/api'

export default function AuthPage() {
  const [mode, setMode]       = useState(() => new URLSearchParams(window.location.search).get('mode') === 'signup' ? 'signup' : 'login')
  const [form, setForm]       = useState({ name: '', email: '', password: '' })
  const [showPw, setShowPw]   = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const { login } = useAuth()
  const nav = useNavigate()

  const onChange = e => { setForm(f => ({ ...f, [e.target.name]: e.target.value })); setError('') }

  const submit = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const trimmed = {
        name: form.name?.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password
      };
      const res = mode === 'signup' ? await authAPI.signup(trimmed) : await authAPI.login(trimmed)
      login(res.data.user, res.data.token)
      console.log('Auth success, delaying nav...')
      setTimeout(() => nav('/dashboard'), 100)
    } catch (err) {
      console.error('Auth error:', err.response?.data || err.message);
      if (err.code === 'ECONNABORTED' || err.message === 'Network Error' || !err.response) {
        setError('Server is waking up or unreachable. Please wait a moment and try again.')
      } else {
        setError(err.response?.data?.detail || 'Something went wrong.')
      }
    } finally { setLoading(false) }
  }

  const isLogin = mode === 'login'

  return (
    <div className="auth-page">
      <aside className="auth-showcase">
        <button className="auth-back" onClick={() => nav('/')}><ArrowLeft size={18} /> Back to home</button>
        <div className="auth-brand"><span className="auth-brand-mark"><Sparkles /></span><span>SKINSIGHT</span></div>
        <div className="auth-showcase-copy"><span className="auth-kicker">YOUR SKIN STORY STARTS HERE</span><h1>{isLogin ? 'Welcome back to better skin care.' : 'Your best skin starts with insight.'}</h1><p>{isLogin ? 'Pick up where you left off with your personalized skin analysis and routine.' : 'Create your profile and discover a routine designed around your skin.'}</p></div>
        <div className="auth-orbit"><div className="auth-orbit-ring" /><div className="auth-orbit-core"><Sparkles /></div><span className="auth-orbit-dot dot-one" /><span className="auth-orbit-dot dot-two" /></div>
        <p className="auth-disclaimer">AI-powered guidance for everyday skincare decisions.</p>
      </aside>

      <main className="auth-content">
        <div className="auth-mobile-brand"><span className="auth-brand-mark"><Sparkles /></span><span>SKINSIGHT</span></div>
        <div className="auth-form-wrap">
          <div className="auth-heading"><span className="auth-kicker">{isLogin ? 'WELCOME BACK' : 'GET STARTED'}</span><h2>{isLogin ? 'Sign in to your account' : 'Create your account'}</h2><p>{isLogin ? 'Enter your details to continue your skin journey.' : 'Join SKINSIGHT and start your personalized skin journey.'}</p></div>

          <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode"><button className={isLogin ? 'active' : ''} onClick={() => { setMode('login'); setError('') }}>Sign In</button><button className={!isLogin ? 'active' : ''} onClick={() => { setMode('signup'); setError('') }}>Sign Up</button></div>

          <form onSubmit={submit} className="auth-form">
            {!isLogin && <div className="auth-field"><label htmlFor="name">Full Name</label><input id="name" name="name" value={form.name} onChange={onChange} placeholder="Your name" required /></div>}
            <div className="auth-field"><label htmlFor="email">Email Address</label><input id="email" name="email" type="email" value={form.email} onChange={onChange} placeholder="you@example.com" required /></div>
            <div className="auth-field"><label htmlFor="password">Password</label><div className="auth-password"><input id="password" name="password" type={showPw ? 'text' : 'password'} value={form.password} onChange={onChange} placeholder="Enter your password" required minLength={6} /><button type="button" aria-label={showPw ? 'Hide password' : 'Show password'} onClick={() => setShowPw(v => !v)}>{showPw ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{!isLogin && <small>Use at least 6 characters.</small>}</div>
            {error && <div className="auth-error"><p>{error}</p></div>}
            <button type="submit" disabled={loading} className="auth-submit">{loading ? <span className="auth-spinner" /> : isLogin ? 'Sign In' : 'Create Account'}</button>
          </form>

          <div className="auth-note"><Sparkles size={15} /><span>Register with any email and a 6-character password to explore the demo.</span></div>
        </div>
      </main>
    </div>
  )
}
