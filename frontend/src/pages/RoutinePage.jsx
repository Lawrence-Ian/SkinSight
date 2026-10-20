import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { historyAPI, routineAPI } from '../utils/api'
import { Check, ChevronLeft, Moon, Sun } from 'lucide-react'

const META = {
  oily: { color: '#b8860b', label: 'Oily' },
  dry: { color: '#4d86b5', label: 'Dry' },
  normal: { color: '#4f917f', label: 'Normal' },
}

function stepTitle(step, index) {
  if (typeof step !== 'string') return step?.name || `Step ${index + 1}`
  const parts = step.split(':')
  return parts.length > 1 ? parts[0].trim() : step
}

function stepDescription(step, index) {
  if (typeof step !== 'string') return step?.description || ''
  const parts = step.split(':')
  return parts.length > 1 ? parts.slice(1).join(':').trim() : step
}

function RoutineStep({ step, index, completed, onToggle, color }) {
  return (
    <label className={`routine-step ${completed ? 'completed' : ''}`}>
      <span className="routine-step-number" style={{ backgroundColor: `${color}18`, color }}>
        {index + 1}
      </span>
      <span className="routine-step-copy">
        <strong>{stepTitle(step, index)}</strong>
        <span>{stepDescription(step, index)}</span>
      </span>
      <input type="checkbox" checked={completed} onChange={onToggle} aria-label={`Mark ${stepTitle(step, index)} complete`} />
      <span className="routine-check" style={{ '--routine-color': color }}><Check size={15} /></span>
    </label>
  )
}

export default function RoutinePage() {
  const navigate = useNavigate()
  const [latestScan, setLatestScan] = useState(null)
  const [routine, setRoutine] = useState(null)
  const [activeTab, setActiveTab] = useState('morning')
  const [completed, setCompleted] = useState({ morning: [], night: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saveError, setSaveError] = useState('')

  useEffect(() => {
    let active = true
    const loadLatestRoutine = async () => {
      try {
        const historyResponse = await historyAPI.getAll()
        const scans = historyResponse.data.history || []
        const latest = scans[0]
        if (!latest) {
          if (active) setLoading(false)
          return
        }
        const routineResponse = await historyAPI.get(latest.id)
        if (!active) return
        setLatestScan(latest)
        setRoutine(routineResponse.data)
        const progressResponse = await routineAPI.getProgress(latest.id)
        const saved = progressResponse.data.progress || {}
        setCompleted({ morning: saved.morning || [], night: saved.night || [] })
      } catch (loadError) {
        if (active) setError('Failed to load your latest routine.')
      } finally {
        if (active) setLoading(false)
      }
    }
    loadLatestRoutine()
    return () => { active = false }
  }, [])

  const steps = routine?.[`${activeTab}_routine`] || []
  const doneSteps = completed[activeTab]?.length || 0
  const progress = steps.length ? Math.round((doneSteps / steps.length) * 100) : 0
  const meta = META[routine?.condition] || META.normal
  const skinLabel = routine?.condition_label || `${meta.label} Skin`
  const scanDate = latestScan?.created_at ? new Date(latestScan.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''

  const updateStep = async index => {
    const current = completed[activeTab] || []
    const next = current.includes(index) ? current.filter(item => item !== index) : [...current, index]
    const updated = { ...completed, [activeTab]: next }
    setCompleted(updated)
    setSaveError('')
    try {
      await routineAPI.saveProgress(latestScan.id, updated)
    } catch {
      setSaveError('Could not save routine progress. Please try again.')
    }
  }

  const tips = useMemo(() => routine?.preventive_tips?.slice(0, 4) || [], [routine])

  if (loading) return <div className="routine-loading"><span /></div>

  if (error) return <div className="routine-empty"><h2>{error}</h2><button onClick={() => navigate('/dashboard')}>Back to Dashboard</button></div>

  if (!routine || !latestScan) return <div className="routine-empty"><h2>No routine yet</h2><p>Complete a skin analysis to receive a personalized routine.</p><button onClick={() => navigate('/analysis')}>Start Skin Analysis</button></div>

  return (
    <div className="routine-page">
      <div className="routine-header">
        <div><span className="routine-kicker">PERSONALIZED FOR {skinLabel.toUpperCase()}</span><h1>Your Skincare Routine</h1><p>AI-curated steps based on your latest skin analysis.</p></div>
        <span className="routine-latest">Latest analysis · {scanDate}</span>
      </div>

      <div className="routine-tabs" role="tablist" aria-label="Routine time of day">
        <button className={activeTab === 'morning' ? 'active' : ''} onClick={() => setActiveTab('morning')}><Sun size={18} /> Morning Routine</button>
        <button className={activeTab === 'night' ? 'active' : ''} onClick={() => setActiveTab('night')}><Moon size={18} /> Night Routine</button>
      </div>

      <section className="routine-progress"><div><strong>{activeTab === 'morning' ? 'Morning' : 'Night'} Progress</strong><span>{doneSteps} of {steps.length} steps complete</span></div><b>{progress}%</b><div className="routine-progress-track"><span style={{ width: `${progress}%`, backgroundColor: meta.color }} /></div></section>

      <section className="routine-steps">{steps.map((step, index) => <RoutineStep key={`${activeTab}-${index}`} step={step} index={index} completed={completed[activeTab]?.includes(index)} onToggle={() => updateStep(index)} color={meta.color} />)}</section>

      {saveError && <p role="status" className="text-sm text-red-600">{saveError}</p>}

      {tips.length > 0 && <section className="routine-tips"><h2>✨ {activeTab === 'morning' ? 'Morning' : 'Night'} Tips for {skinLabel}</h2><ul>{tips.map((tip, index) => <li key={index}>{tip}</li>)}</ul></section>}
      <button className="routine-back" onClick={() => navigate('/dashboard')}><ChevronLeft size={16} /> Back to dashboard</button>
    </div>
  )
}
