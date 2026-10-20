// src/pages/ResultPage.jsx
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft, RotateCcw, Sun, Moon, ShoppingBag, Lightbulb, Phone, ChevronDown, ChevronUp, Star, Camera } from 'lucide-react'
import { historyAPI } from '../utils/api'

const META = {
  oily:   { bg:'#FFF9E6', border:'#FFE082', color:'#B8860B', emoji:'✨' },
  dry:    { bg:'#E8F4FD', border:'#90CAF9', color:'#1565C0', emoji:'💙' },
  normal: { bg:'#E8F5E9', border:'#A5D6A7', color:'#2E7D32', emoji:'💚' },
}

function Bar({ label, value, isTop }) {
  const [w, setW] = useState(0)
  useEffect(() => { setTimeout(() => setW(Math.round(value * 100)), 80) }, [value])
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-medium">
        <span className="capitalize text-skin-text">{label.replace('_', ' ')}</span>
        <span className="text-skin-muted">{Math.round(value * 100)}%</span>
      </div>
      <div className="prog-track">
        <div className="prog-fill" style={{ width: `${w}%`, background: isTop ? '#E36A6A' : '#FFB2B2' }} />
      </div>
    </div>
  )
}

function Section({ title, icon: Icon, children, open: defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card mb-3">
      <button onClick={() => setOpen(v => !v)} className="w-full flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-skin-a1 bg-opacity-35 flex items-center justify-center">
            <Icon size={15} className="text-skin-a2" />
          </div>
          <span className="font-semibold text-sm text-skin-text">{title}</span>
        </div>
        {open ? <ChevronUp size={17} className="text-skin-muted" /> : <ChevronDown size={17} className="text-skin-muted" />}
      </button>
      {open && <div className="mt-4 pt-4 border-t border-skin-border">{children}</div>}
    </div>
  )
}

const Steps = ({ items }) => (
  <ol className="space-y-2.5">
    {items.map((s, i) => (
      <li key={i} className="flex gap-3">
        <span className="w-6 h-6 rounded-full bg-skin-a2 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
        <p className="text-sm text-skin-muted leading-relaxed">{s}</p>
      </li>
    ))}
  </ol>
)

const Tips = ({ items }) => (
  <ul className="space-y-2">
    {items.map((t, i) => (
      <li key={i} className="flex gap-2 text-sm text-skin-muted leading-relaxed">
        <span className="text-skin-a2 mt-0.5 flex-shrink-0">✓</span>{t}
      </li>
    ))}
  </ul>
)

function ProductImage({ product }) {
  const [failed, setFailed] = useState(false)
  if (!product.image_url || failed) {
    return <div className="w-16 h-16 rounded-xl bg-skin-a1 bg-opacity-30 flex items-center justify-center text-center text-[10px] font-semibold text-skin-a2 flex-shrink-0 px-1">{product.brand || 'Product'}</div>
  }
  return <img src={product.image_url} alt={`${product.brand || ''} ${product.name}`} onError={() => setFailed(true)} className="w-16 h-16 rounded-xl object-contain bg-white flex-shrink-0" />
}

export default function ResultPage() {
  const { state } = useLocation()
  const { scanId } = useParams()
  const nav = useNavigate()
  const [loadedResult, setLoadedResult] = useState(null)
  const [loadError, setLoadError] = useState('')
  const r = state?.result || loadedResult

  useEffect(() => {
    if (!scanId) {
      if (!state?.result) nav('/dashboard')
      return undefined
    }

    let active = true
    historyAPI.get(scanId)
      .then(res => { if (active) setLoadedResult(res.data) })
      .catch(() => { if (active) setLoadError('Could not load this scan analysis.') })
    return () => { active = false }
  }, [nav, scanId, state?.result])

  if (loadError) return <div className="card mx-4 my-5 text-center py-10"><p className="text-skin-muted mb-3">{loadError}</p><button onClick={() => nav('/history')} className="btn-ghost text-sm">Back to History</button></div>
  if (!r) return <div className="p-8 text-center text-skin-muted">Loading scan analysis...</div>

  const m        = META[r.condition] || META.normal
  const maxScore = Math.max(...Object.values(r.all_scores || {}))

  return (
    <div className="px-4 sm:px-5 py-4 sm:py-5 space-y-4 anim-fadeup">
      <button onClick={() => nav('/dashboard')} className="flex items-center gap-2 text-skin-muted hover:text-skin-text text-sm font-medium">
        <ArrowLeft size={17} /> New Scan
      </button>

      {/* Result hero card */}
      <div className="rounded-3xl p-4 sm:p-5 border-2 space-y-3 anim-fadeup"
        style={{ background: m.bg, borderColor: m.border }}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold tracking-widest uppercase mb-1" style={{ color: m.color }}>Detected via Live Camera</p>
            <h2 className="font-display text-xl sm:text-2xl font-bold leading-tight" style={{ color: m.color }}>
              {m.emoji} {r.condition_label}
            </h2>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-skin-muted mb-0.5">Confidence</p>
            <p className="font-display text-3xl sm:text-4xl font-bold" style={{ color: m.color }}>{r.confidence_percent}%</p>
          </div>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: m.color, opacity: 0.85 }}>{r.description}</p>
        <div className="flex items-center gap-2 text-xs" style={{ color: m.color, opacity: 0.7 }}>
          <Camera size={12} />
          <span>Captured from live camera</span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button 
          onClick={() => nav(`/routine`)}
          className="flex-1 py-3 rounded-2xl font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all"
          style={{ backgroundColor: m.color, color: 'white', opacity: 0.9 }}
          onMouseEnter={(e) => e.target.style.opacity = '1'}
          onMouseLeave={(e) => e.target.style.opacity = '0.9'}
        >
          <ShoppingBag size={16} /> View Your Routines
        </button>
      </div>

      {/* Score breakdown */}
      {r.all_scores && (
        <div className="card space-y-3">
          <p className="font-semibold text-sm flex items-center gap-2">
            <Star size={15} className="text-skin-a2" /> Confidence Breakdown
          </p>
          {Object.entries(r.all_scores).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
            <Bar key={k} label={k} value={v} isTop={v === maxScore} />
          ))}
          {r.using_mock_model && <p className="text-[11px] text-skin-muted italic">* Simulated predictions (demo mode)</p>}
        </div>
      )}

      <Section title="☀️ Morning Routine" icon={Sun} open>
        <Steps items={r.morning_routine || []} />
      </Section>

      <Section title="🌙 Night Routine" icon={Moon}>
        <Steps items={r.night_routine || []} />
      </Section>

      {r.products?.length > 0 && (
        <Section title="🛍 Recommended Products" icon={ShoppingBag}>
          <div className="space-y-2.5">
            {r.products.map((p, i) => (
              <div key={i} className="flex gap-3 p-3 bg-skin-bg rounded-2xl">
                <ProductImage product={p} />
                <div>
                  <p className="font-semibold text-sm text-skin-text">{p.name}</p>
                  {p.brand && <p className="text-xs text-skin-muted">{p.brand}</p>}
                  <p className="text-xs text-skin-muted">{p.ingredient}</p>
                  <p className="text-xs text-skin-a2 font-medium mt-0.5">{p.purpose}</p>
                  {p.price_range && <p className="text-xs text-skin-muted mt-0.5">Typical price: {p.price_range}</p>}
                  {p.product_url && <a href={p.product_url} target="_blank" rel="noreferrer" className="text-xs text-skin-a2 underline mt-1 inline-block">Verify product packaging</a>}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {r.preventive_tips?.length > 0 && (
        <Section title="💡 Preventive Tips" icon={Lightbulb}>
          <Tips items={r.preventive_tips} />
        </Section>
      )}



      {r.ingredients_to_avoid?.length > 0 && (
        <div className="card mb-3">
          <p className="font-semibold text-sm text-red-500 mb-3">⛔ Ingredients to Avoid</p>
          <div className="flex flex-wrap gap-2">
            {r.ingredients_to_avoid.map((x, i) => (
              <span key={i} className="text-xs px-3 py-1 rounded-full bg-red-50 text-red-500 border border-red-100">{x}</span>
            ))}
          </div>
        </div>
      )}

      {r.consult_dermatologist && (
        <div className="card-soft border border-skin-a1 space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-skin-a1 bg-opacity-40 flex items-center justify-center">
              <Phone size={18} className="text-skin-a2" />
            </div>
            <div>
              <p className="font-bold text-skin-text">Consult a Dermatologist</p>
              <p className="text-xs text-skin-muted">Professional evaluation recommended</p>
            </div>
          </div>
          <p className="text-sm text-skin-muted">Our AI detected features that warrant professional examination. Please book an appointment.</p>
        </div>
      )}

      <p className="text-center text-xs text-skin-muted">
        Scanned {new Date(r.timestamp).toLocaleString()}
      </p>

      <button onClick={() => nav('/dashboard')} className="btn-ghost w-full flex items-center justify-center gap-2">
        <RotateCcw size={15} /> Scan Again
      </button>
      <div className="h-2" />
    </div>
  )
}
