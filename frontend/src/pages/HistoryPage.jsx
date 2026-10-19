// src/pages/HistoryPage.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, RefreshCw, TrendingUp, Camera } from 'lucide-react'
import { historyAPI } from '../utils/api'

const META = {
  acne:   { emoji:'🔴', label:'Acne',   color:'#C0504D' },
  oily:   { emoji:'✨', label:'Oily',    color:'#B8860B' },
  dry:    { emoji:'💙', label:'Dry',     color:'#1565C0' },
  normal: { emoji:'💚', label:'Normal',  color:'#2E7D32' },
}

export default function HistoryPage() {
  const [history, setHistory]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const nav = useNavigate()

  const load = async () => {
    setLoading(true)
    try { const r = await historyAPI.getAll(); setHistory(r.data.history) }
    catch { setError('Could not load scan history.') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const del = async id => {
    try { await historyAPI.delete(id); setHistory(h => h.filter(s => s.id !== id)) }
    catch { alert('Failed to delete.') }
  }

  const avg = history.length
    ? Math.round(history.reduce((a, h) => a + h.confidence_percent, 0) / history.length)
    : 0

  const topCondition = history.length
    ? Object.entries(history.reduce((acc, h) => { acc[h.condition] = (acc[h.condition] || 0) + 1; return acc }, {}))
        .sort((a, b) => b[1] - a[1])[0]
    : null

  return (
    <div className="px-4 sm:px-5 py-4 sm:py-5 space-y-5 anim-fadeup">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl sm:text-2xl font-bold text-skin-text">Scan History</h1>
          <p className="text-skin-muted text-sm mt-0.5">All live camera scans</p>
        </div>
        <button onClick={load} className="w-9 h-9 rounded-xl bg-skin-card border border-skin-border flex items-center justify-center hover:bg-skin-a1/30 transition-colors">
          <RefreshCw size={14} className="text-skin-muted" />
        </button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-24 rounded-3xl animate-pulse bg-skin-card" />)}
        </div>
      ) : error ? (
        <div className="card text-center py-10">
          <p className="text-skin-muted mb-3">{error}</p>
          <button onClick={load} className="btn-ghost text-sm">Retry</button>
        </div>
      ) : history.length === 0 ? (
        <div className="card text-center py-16 space-y-4">
          <div className="text-5xl">📷</div>
          <div>
            <p className="font-semibold text-skin-text">No scans yet</p>
            <p className="text-sm text-skin-muted mt-1">Use the live camera to scan your skin</p>
          </div>
          <button onClick={() => nav('/dashboard')} className="btn-primary px-8 py-2.5 text-sm">Start Scanning</button>
        </div>
      ) : (
        <>
          {/* Summary stats */}
          {history.length > 1 && (
            <div className="card-soft space-y-3">
              <div className="flex items-center gap-2">
                <TrendingUp size={15} className="text-skin-a2" />
                <p className="font-semibold text-sm">Your Skin Progress</p>
              </div>
              <div className="grid grid-cols-3 gap-2 sm:gap-3 text-center">
                {[
                  { val: history.length, label: 'Total Scans' },
                  { val: topCondition ? (META[topCondition[0]]?.emoji || '—') : '—', label: 'Most Common' },
                  { val: `${avg}%`, label: 'Avg Confidence' },
                ].map(({ val, label }) => (
                  <div key={label} className="bg-skin-bg rounded-2xl py-3 border border-skin-border">
                    <p className="font-display text-lg sm:text-xl font-bold text-skin-a2">{val}</p>
                    <p className="text-xs text-skin-muted mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cards */}
          <div className="space-y-3">
            {history.map(s => {
              const m = META[s.condition] || META.normal
              return (
                <div key={s.id} className="card anim-fadeup cursor-pointer" role="button" tabIndex={0}
                  onClick={() => nav(`/result/${s.id}`)}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); nav(`/result/${s.id}`) } }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0"
                        style={{ background: `${m.color}18` }}>{m.emoji}</div>
                      <div>
                        <p className="font-semibold text-skin-text">{m.label}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <div className="w-16 h-1.5 rounded-full bg-skin-border overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${s.confidence_percent}%`, background: m.color }} />
                          </div>
                          <span className="text-xs text-skin-muted">{s.confidence_percent}%</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={(e) => { e.stopPropagation(); del(s.id); }}
                        className="w-8 h-8 rounded-xl bg-skin-bg border border-skin-border flex items-center justify-center hover:bg-red-50 hover:border-red-200 transition-colors">
                        <Trash2 size={13} className="text-skin-muted" />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-3 pt-3 border-t border-skin-border">
                    <div className="flex items-center gap-1 text-xs text-skin-muted">
                      <Camera size={11} />
                      <span>Live camera</span>
                    </div>
                    <span className="text-skin-border">·</span>
                    <span className="text-xs text-skin-muted">
                      {new Date(s.created_at).toLocaleDateString(undefined, { weekday:'short', month:'short', day:'numeric' })}
                      {' · '}
                      {new Date(s.created_at).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
