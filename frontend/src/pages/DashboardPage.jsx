// src/pages/DashboardPage.jsx
// LIVE CAMERA ONLY — no file upload whatsoever
import { useRef, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Camera, Check, CircleAlert, Crosshair, Droplets, RefreshCw, ShieldCheck, Sparkles, Zap, Info, FlipHorizontal } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { analysisAPI, historyAPI } from '../utils/api'
import { detectFaces, getFaceDetector } from '../utils/faceDetector'

const COUNTDOWN_SEC = 3

const getTimeGreeting = () => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

export default function DashboardPage({ scannerOnly = false }) {
  const { user }          = useAuth()
  const navigate          = useNavigate()
  const videoRef          = useRef(null)
  const canvasRef         = useRef(null)
  const streamRef         = useRef(null)
  const faceDetectorRef   = useRef(null)
  const faceDetectorPromiseRef = useRef(null)

  const [camState, setCamState]   = useState('idle')   // idle | requesting | live | countdown | capturing | error
  const [facingMode, setFacingMode] = useState('user')
  const [countdown, setCountdown]   = useState(0)
  const [analyzing, setAnalyzing]   = useState(false)
  const [error, setError]           = useState('')
  const [camError, setCamError]     = useState('')
  const [tip, setTip]               = useState(0)
  const [showScanner, setShowScanner] = useState(scannerOnly)
  const [timeGreeting, setTimeGreeting] = useState(getTimeGreeting)
  const [detection, setDetection] = useState({
    facePosition: 'Searching',
    faceCount: 0,
    faceDetectionAvailable: false,
    lighting: 'Checking',
    clarity: 'Checking',
    distance: 'Checking',
  })
  const [recentanalysis, setRecentanalysis] = useState([])

  useEffect(() => {
    const timer = setInterval(() => setTimeGreeting(getTimeGreeting()), 60 * 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    let active = true
    historyAPI.getAll()
      .then(res => { if (active) setRecentanalysis(res.data.history || []) })
      .catch(() => { if (active) setRecentanalysis([]) })
    return () => { active = false }
  }, [])

  const TIPS = [
    'Position your face inside the oval',
    'Find good natural lighting',
    'Hold your device at arm\'s length',
    'Look straight into the camera',
    'Remove glasses for best results',
  ]

  const latestAnalysis = recentanalysis[0]
  const skinType = latestAnalysis?.condition
    ? `${latestAnalysis.condition.charAt(0).toUpperCase()}${latestAnalysis.condition.slice(1)} Skin`
    : 'Not analyzed'
  const formatScores = scores => Object.entries(scores || {})
    .slice(0, 3)
    .map(([name, score]) => `${name.charAt(0).toUpperCase()}${name.slice(1)} ${Math.round(score * 100)}%`)
    .join(' · ')
  const formatScanDate = timestamp => new Date(timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

  useEffect(() => {
    const t = setInterval(() => setTip(i => (i + 1) % TIPS.length), 3500)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    if (!showScanner || (camState !== 'live' && camState !== 'countdown')) {
      setDetection({
        facePosition: 'Searching',
        faceCount: 0,
        faceDetectionAvailable: false,
        lighting: 'Checking',
        clarity: 'Checking',
        distance: 'Checking',
      })
      return undefined
    }

    const measureFrame = async () => {
      const video = videoRef.current
      if (!video || video.readyState < 2 || !video.videoWidth) return

      const canvas = document.createElement('canvas')
      canvas.width = 160
      canvas.height = 120
      const context = canvas.getContext('2d', { willReadFrequently: true })
      context.drawImage(video, 0, 0, canvas.width, canvas.height)
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
      let brightness = 0
      let brightnessSquared = 0
      let edgeChange = 0
      let previous = null

      for (let index = 0; index < pixels.length; index += 4) {
        const luminance = (pixels[index] * 0.299) + (pixels[index + 1] * 0.587) + (pixels[index + 2] * 0.114)
        brightness += luminance
        brightnessSquared += luminance * luminance
        if (previous !== null) edgeChange += Math.abs(luminance - previous)
        previous = luminance
      }

      const pixelCount = pixels.length / 4
      const averageBrightness = brightness / pixelCount
      const brightnessVariance = (brightnessSquared / pixelCount) - (averageBrightness * averageBrightness)
      const averageEdgeChange = edgeChange / Math.max(pixelCount - 1, 1)
      const lighting = averageBrightness < 48 ? 'Too Dark' : averageBrightness > 212 ? 'Too Bright' : 'Good'
      const clarity = averageEdgeChange > 18 && brightnessVariance > 260 ? 'Sharp' : averageEdgeChange > 9 ? 'Fair' : 'Blurry'

      let facePosition = 'Searching'
      let faceCount = 0
      let faceDetectionAvailable = Boolean(faceDetectorRef.current)
      let distance = 'Checking'
      try {
        if (!faceDetectorRef.current) {
          if (!faceDetectorPromiseRef.current) faceDetectorPromiseRef.current = getFaceDetector()
          faceDetectorRef.current = await faceDetectorPromiseRef.current
        }
        const faces = await detectFaces(faceDetectorRef.current, canvas)
        faceDetectionAvailable = true
        faceCount = faces.length
        const face = faces[0]
        if (faces.length === 0) {
          facePosition = 'No Face'
        } else if (faces.length > 1) {
          facePosition = 'Multiple Faces'
        } else if (face?.boundingBox) {
          const box = face.boundingBox
          const centerX = box.originX + (box.width / 2)
          const centerY = box.originY + (box.height / 2)
          facePosition = Math.abs(centerX - (canvas.width / 2)) < canvas.width * 0.16 &&
            Math.abs(centerY - (canvas.height / 2)) < canvas.height * 0.2
            ? 'Centered'
            : 'Reposition'
          const faceArea = (box.width * box.height) / (canvas.width * canvas.height)
          distance = faceArea < 0.12 ? 'Move Closer' : faceArea > 0.55 ? 'Move Back' : 'Optimal'
        }
      } catch (detectorError) {
        console.error('Face detector error:', detectorError)
        faceDetectorRef.current = null
        faceDetectorPromiseRef.current = null
        facePosition = 'Face Detection Unavailable'
        faceDetectionAvailable = false
      }

      setDetection({ facePosition, faceCount, faceDetectionAvailable, lighting, clarity, distance })
    }

    const timer = window.setInterval(measureFrame, 700)
    measureFrame()
    return () => window.clearInterval(timer)
  }, [camState, showScanner])

  // ── Start camera ─────────────────────────────────────────────────────────
  const startCamera = useCallback(async (facing = facingMode) => {
    setError(''); setCamError('')
    setCamState('requesting')

    // Stop any existing stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }

    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        throw new Error('Camera access requires HTTPS or localhost in a supported browser.')
      }

      // Try with flexible constraints first (mobile compatibility)
      let constraints = {
        video: {
          facingMode: facing,
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false,
      }

      let stream
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints)
      } catch (firstErr) {
        console.warn('Constraints failed, trying basic video request:', firstErr.name)
        // Fallback: try with minimal constraints
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing },
          audio: false,
        })
      }
      
      if (!stream) {
        throw new Error('Failed to get camera stream')
      }

      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        try {
          await videoRef.current.play()
        } catch (playErr) {
          console.error('Video play error:', playErr)
        }
      }
      setCamState('live')
    } catch (err) {
      // Provide specific error messages
      let msg = ''
      
      if (err.name === 'NotAllowedError') {
        msg = 'Camera permission denied. Please allow camera access in your browser settings.'
      } else if (err.name === 'NotFoundError') {
        msg = 'No camera found on this device.'
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        msg = 'Camera is already in use. Close other camera apps and try again.'
      } else if (err.name === 'SecurityError') {
        msg = 'Camera access blocked by browser security. Check your site is using HTTPS or localhost.'
      } else if (err.name === 'OverconstrainedError') {
        msg = 'Camera does not support the requested resolution. Please try again.'
      } else {
        msg = `Camera error: ${err.message || err.name || 'Unknown error'}`
      }
      
      console.error('Camera error details:', err.name, err.message)
      setCamError(msg)
      setCamState('error')
    }
  }, [facingMode])

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    }
  }, [])

  // ── Flip camera ───────────────────────────────────────────────────────────
  const flipCamera = () => {
    const next = facingMode === 'user' ? 'environment' : 'user'
    setFacingMode(next)
    startCamera(next)
  }

  // ── Capture after countdown ───────────────────────────────────────────────
  const beginCapture = () => {
    if (camState !== 'live') return
    const faceCheckRequired = detection.faceDetectionAvailable
    const captureBlocked =
      !streamRef.current ||
      detection.lighting !== 'Good' ||
      (faceCheckRequired && (detection.facePosition !== 'Centered' || detection.faceCount !== 1))
    if (captureBlocked) {
      if (!streamRef.current) {
        setError('Camera is unavailable. Please start the camera again.')
      } else if (detection.lighting === 'Too Dark' || detection.lighting === 'Checking') {
        setError('Please move to a brighter area before capturing.')
      } else if (detection.lighting !== 'Good') {
        setError('Please reduce the lighting or glare before capturing.')
      } else if (detection.faceCount === 0 || detection.facePosition === 'No Face') {
        setError('Position one face inside the guide before capturing.')
      } else if (detection.faceCount > 1 || detection.facePosition === 'Multiple Faces') {
        setError('Only one face may be visible before capturing.')
      } else if (detection.facePosition !== 'Centered') {
        setError('Center one face inside the guide before capturing.')
      }
      return
    }
    setError('')
    setCamState('countdown')
    let count = COUNTDOWN_SEC
    setCountdown(count)
    const t = setInterval(() => {
      count -= 1
      if (count <= 0) {
        clearInterval(t)
        setCountdown(0)
        captureAndAnalyze()
      } else {
        setCountdown(count)
      }
    }, 1000)
  }

  // ── Capture frame & send to backend ──────────────────────────────────────
  const captureAndAnalyze = async () => {
    if (
      !streamRef.current ||
      detection.lighting !== 'Good' ||
      (detection.faceDetectionAvailable && (detection.facePosition !== 'Centered' || detection.faceCount !== 1))
    ) {
      setError('Camera conditions changed. Keep one face centered in good lighting and try again.')
      setCountdown(0)
      setCamState('live')
      return
    }

    setCamState('capturing')
    setAnalyzing(true)
    setError('')

    const video  = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) { setError('Camera not ready.'); setAnalyzing(false); setCamState('live'); return }

    canvas.width  = video.videoWidth  || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')

    // Mirror the capture if using front camera
    if (facingMode === 'user') {
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Get base64 JPEG
    const frame = canvas.toDataURL('image/jpeg', 0.88)

    try {
      const res = await analysisAPI.scanFrame(frame)
      localStorage.setItem('sk_latest_products', JSON.stringify(res.data.products || []))
      navigate('/result', { state: { result: res.data } })
    } catch (err) {
      const msg = err.response?.data?.detail || 'Analysis failed. Please try again.'
      setError(msg)
      setCamState('live')
    } finally {
      setAnalyzing(false)
    }
  }

  if (!showScanner) {
    return (
      <div className="dashboard-home">
        <div className="dashboard-heading">
          <div><p className="dashboard-eyebrow">☕ {timeGreeting}</p><h1>{user?.name || 'Welcome back'}</h1><p>Ready to check your skin today?</p></div>
          <span className="skin-status"><i /> {skinType}</span>
        </div>
        <section className="dashboard-hero-card"><div><p>{latestAnalysis ? `Last scan: ${formatScanDate(latestAnalysis.created_at)}` : 'No scans yet'}</p><h2>Start Skin Analysis</h2><span>Get an updated reading of your skin with our AI<br className="desktop-only" /> scanner.</span><button onClick={() => navigate('/analysis')}><Camera size={17} /> Analyze Now <Sparkles size={15} /></button></div><div className="hero-rings"><span /><span /></div></section>
        <section className="dashboard-stats"><article><strong className="gold-number">{recentanalysis.length}</strong><b>Total Scans</b><span>Analysis done</span></article></section>
        <div className="dashboard-grid">
          <div className="dashboard-main-column">
            <section className="dashboard-panel quick-actions"><h2>Quick Actions</h2><div><button onClick={() => navigate('/analysis')}><span className="action-icon pink-bg"><Camera /></span><b>Analyze Skin</b></button><button onClick={() => navigate('/routine')}><span className="action-icon mint-bg"><Check /></span><b>My Routine</b></button><button onClick={() => navigate('/map')}><span className="action-icon blue-bg"><Droplets /></span><b>Find Care</b></button><button onClick={() => navigate('/history')}><span className="action-icon gold-bg"><Sparkles /></span><b>History</b></button></div></section>
            <section className="dashboard-panel recent-panel"><h2>Recent Analysis</h2>{recentanalysis.length ? recentanalysis.slice(0, 3).map(scan => <div className="analysis-row" key={scan.id}><span className="score-ring">{Math.round(scan.confidence_percent)}</span><div><b>{scan.condition.charAt(0).toUpperCase()}{scan.condition.slice(1)} Skin</b><p>{formatScores(scan.all_scores)}</p></div><time>{formatScanDate(scan.created_at)}</time></div>) : <p className="dashboard-empty">No analysis yet. Start a live scan to see your results here.</p>}</section>
          </div>
          <aside className="dashboard-side-column"><section className="dashboard-panel profile-panel"><h2>Skin Profile</h2><div><span>Skin Type</span><b>{skinType}</b></div><div><span>AI Confidence</span><b>{latestAnalysis ? `${latestAnalysis.confidence_percent}%` : '—'}</b></div><button onClick={() => navigate('/analysis')}>Update Analysis</button></section><section className="dashboard-panel tips-panel"><h2>Skincare Tips</h2><div><Droplets /><p><b>Stay Hydrated</b><span>Drink at least 8 glasses of water daily for plump, healthy-looking skin.</span></p></div><div><CircleAlert /><p><b>Never Skip SPF</b><span>UV damage is the #1 cause of premature skin aging.</span></p></div></section></aside>
        </div>
      </div>
    )
  }

  if (!showScanner) {
    return (
      <div className="dashboard-home">
        <div className="dashboard-heading"><div><p className="dashboard-eyebrow">☕ {timeGreeting}</p><h1>{user?.name || 'Welcome back'}</h1><p>Ready to check your skin today?</p></div><span className="skin-status"><i /> Skin analysis ready</span></div>
        <section className="dashboard-hero-card"><div><p>Last scan: Sep 15</p><h2>Start Skin Analysis</h2><span>Get an updated reading of your skin with our AI<br className="desktop-only" /> scanner.</span><button onClick={() => navigate('/analysis')}><Camera size={17} /> Analyze Now <Sparkles size={15} /></button></div><div className="hero-rings"><span /><span /></div></section>
        <section className="dashboard-stats"><article><strong className="gold-number">{recentanalysis.length}</strong><b>Total Scans</b><span>Analysis done</span></article></section>
        <div className="dashboard-grid"><div className="dashboard-main-column"><section className="dashboard-panel quick-actions"><h2>Quick Actions</h2><div><button onClick={() => navigate('/analysis')}><span className="action-icon pink-bg"><Camera /></span><b>Analyze Skin</b></button><button onClick={() => navigate('/routine')}><span className="action-icon mint-bg"><Check /></span><b>My Routine</b></button><button onClick={() => navigate('/map')}><span className="action-icon blue-bg"><Droplets /></span><b>Find Care</b></button><button onClick={() => navigate('/history')}><span className="action-icon gold-bg"><Sparkles /></span><b>History</b></button></div></section><section className="dashboard-panel recent-panel"><h2>Recent Analysis</h2>{[['76','Sep 15','Oily 59% · Dryness 33% · Normal 8%'],['72','Sep 14','Oily 55% · Dryness 25% · Normal 20%'],['68','Aug 31','Oily 45% · Dryness 35% · Normal 20%']].map(([score,date,details]) => <div className="analysis-row" key={date}><span className="score-ring">{score}</span><div><b>Skin Type Analysis</b><p>{details}</p></div><time>{date}</time></div>)}</section></div><aside className="dashboard-side-column"><section className="dashboard-panel profile-panel"><h2>Skin Profile</h2><div><span>Skin Type</span><b>Not analyzed</b></div><div><span>AI Confidence</span><b>—</b></div><button onClick={() => navigate('/analysis')}>Update Analysis</button></section><section className="dashboard-panel tips-panel"><h2>Skincare Tips</h2><div><Droplets /><p><b>Stay Hydrated</b><span>Drink at least 8 glasses of water daily for plump, healthy-looking skin.</span></p></div><div><CircleAlert /><p><b>Never Skip SPF</b><span>UV damage is the #1 cause of premature skin aging.</span></p></div></section></aside></div>
      </div>
    )
  }

  if (showScanner) {
    return (
      <div className="analysis-page">
        <div className="analysis-page-heading"><button onClick={() => { setShowScanner(false); navigate('/dashboard') }}><ArrowLeft size={19} /></button><div><h1>AI Skin Scanner</h1><p>CNN-powered facial analysis</p></div></div>
        <div className="analysis-layout">
          <section className="analysis-camera-column">
            <div className="analysis-camera-frame">
              <video ref={videoRef} autoPlay playsInline muted className="analysis-video" style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'none', display: (camState === 'live' || camState === 'countdown') ? 'block' : 'none' }} />
              <canvas ref={canvasRef} className="hidden" />
              {camState === 'idle' && <div className="analysis-camera-idle"><Camera size={40} /><p>Camera ready</p><span>Start the live scanner when you are ready.</span></div>}
              {camState === 'requesting' && <div className="analysis-camera-idle"><span className="analysis-spinner" /><p>Requesting camera access</p></div>}
              {camState === 'error' && <div className="analysis-camera-idle"><Camera size={34} /><p>{camError}</p><button onClick={() => startCamera()}>Try Again</button></div>}
              {(camState === 'live' || camState === 'countdown') && <><div className="analysis-chip face-chip"><i /> {detection.facePosition === 'Centered' ? 'Face Detected' : detection.facePosition}</div><div className="analysis-chip light-chip">⚡ {detection.lighting}</div><div className="analysis-face-guide"><span /><span /><span /><span /></div><div className="analysis-detected">{detection.facePosition === 'Centered' ? '✓ Face detected' : '⌾ Align your face'}</div><button className="analysis-flip" onClick={flipCamera}><FlipHorizontal size={17} /></button>{camState === 'countdown' && <div className="analysis-countdown">{countdown}</div>}</>}
              {camState === 'capturing' && <div className="analysis-capturing"><span className="analysis-spinner" /><p>Analyzing your skin...</p><small>Running CNN model</small></div>}
            </div>
            <div className="analysis-camera-actions">
              {camState === 'idle' && <button className="analysis-start" onClick={() => startCamera()}><Camera size={18} /> Start Skin Analysis</button>}
              {camState === 'live' && <button className="analysis-start" onClick={beginCapture} disabled={!streamRef.current || detection.lighting !== 'Good' || (detection.faceDetectionAvailable && (detection.facePosition !== 'Centered' || detection.faceCount !== 1))}><Camera size={18} /> Start Skin Analysis</button>}
              {camState === 'countdown' && <button className="analysis-start" disabled><Camera size={18} /> Hold still...</button>}
              <p className="analysis-helper">
                {camState === 'live' && !detection.faceDetectionAvailable && detection.lighting === 'Good'
                  ? 'Good lighting detected — center your face in the guide'
                  : camState === 'live' && detection.facePosition !== 'Centered'
                  ? 'Center one face inside the guide before starting the scan'
                  : camState === 'live' && detection.lighting !== 'Good'
                  ? 'Good lighting is required before starting the scan'
                  : 'Hold still for 3 seconds while scanning'}
              </p>
            </div>
          </section>
          <section className="analysis-details">
            <div className="analysis-intro"><h2>Position your face</h2><p>Center your face in the oval guide. The AI will scan multiple skin parameters in real time.</p></div>
            <section className="analysis-panel detection-panel"><h3>Live Detection Status</h3><div><span>Face Position</span><b className={`detection-${detection.facePosition.toLowerCase().replaceAll(' ', '-')}`}>{detection.facePosition}</b></div><div><span>Lighting Quality</span><b className={`detection-${detection.lighting.toLowerCase().replaceAll(' ', '-')}`}>{detection.lighting}</b></div><div><span>Image Clarity</span><b className={`detection-${detection.clarity.toLowerCase()}`}>{detection.clarity}</b></div><div><span>Distance</span><b className={`detection-${detection.distance.toLowerCase().replaceAll(' ', '-')}`}>{detection.distance}</b></div></section>
            <section className="analysis-panel analysis-tip"><Crosshair /><div><h3>For best results</h3><p>Look directly at the camera with a neutral expression. Avoid strong shadows across your face.</p></div></section>
          </section>
        </div>
      </div>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="px-4 sm:px-5 py-4 sm:py-5 space-y-4 sm:space-y-5 anim-fadeup">
      {/* Greeting */}
      <div>
        <p className="text-skin-muted text-sm">Good day,</p>
        <h1 className="font-display text-xl sm:text-2xl font-bold text-skin-text">{user?.name?.split(' ')[0]} ✨</h1>
        <p className="text-skin-muted text-sm mt-0.5">Point your camera at your face and scan live.</p>
      </div>

      {/* Tip strip */}
      <div className="card-soft flex items-center gap-3 py-3">
        <Info size={16} className="text-skin-a2 flex-shrink-0" />
        <p className="text-xs text-skin-muted transition-all duration-500">{TIPS[tip]}</p>
      </div>

      {/* Mobile HTTPS notice */}
      {typeof window !== 'undefined' && window.location.protocol === 'http:' && !window.location.hostname.includes('localhost') && (
        <div className="card-soft border border-skin-a1/20 flex items-start gap-3 py-3">
          <Info size={16} className="text-skin-a1 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-skin-muted">
            <p className="font-medium text-skin-a1 mb-1">Mobile users: Use HTTPS</p>
            <p>For camera access on mobile devices, your connection must be secure (HTTPS). Contact your admin to enable HTTPS or test on <code className="text-xs bg-white/5 px-1 rounded">localhost</code>.</p>
          </div>
        </div>
      )}

      {/* ── Camera Viewfinder ── */}
      <div className="relative w-full max-w-[18.5rem] sm:max-w-[21rem] mx-auto aspect-[3/4] rounded-3xl overflow-hidden bg-zinc-900 shadow-[0_8px_40px_rgba(61,43,31,0.18)]">

        {/* Video element — always in DOM */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
          style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'none', display: (camState === 'live' || camState === 'countdown') ? 'block' : 'none' }}
          onLoadedMetadata={() => console.log('Video metadata loaded')}
          onError={(e) => console.error('Video element error:', e)}
        />
        <canvas ref={canvasRef} className="hidden" />

        {/* Idle state */}
        {camState === 'idle' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-5 bg-zinc-900">
            <div className="w-24 h-24 rounded-full bg-white/10 flex items-center justify-center">
              <Camera size={42} className="text-white/70" />
            </div>
            <div className="text-center px-8">
              <p className="text-white font-semibold text-lg">Live Camera</p>
              <p className="text-white/50 text-sm mt-1">Tap below to start your skin scan</p>
            </div>
            <button onClick={() => startCamera()} className="btn-primary px-8 py-3 flex items-center gap-2 text-sm">
              <Camera size={16} /> Start Camera
            </button>
          </div>
        )}

        {/* Requesting permission */}
        {camState === 'requesting' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-zinc-900">
            <div className="w-10 h-10 rounded-full border-3 border-skin-a1 border-t-transparent animate-spin" />
            <p className="text-white/70 text-sm">Requesting camera access…</p>
          </div>
        )}

        {/* Camera error */}
        {camState === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-zinc-900 px-8 text-center">
            <div className="w-16 h-16 rounded-full bg-skin-a1/20 flex items-center justify-center">
              <Camera size={28} className="text-skin-a1" />
            </div>
            <p className="text-white/80 text-sm leading-relaxed">{camError}</p>
            <button onClick={() => startCamera()} className="btn-primary px-6 py-2.5 text-sm flex items-center gap-2">
              <RefreshCw size={14} /> Try Again
            </button>
          </div>
        )}

        {/* Oval face guide + scan line — shown when camera is live or in countdown */}
        {(camState === 'live' || camState === 'countdown') && (
          <>
            {/* Dark vignette cutout */}
            <div className="camera-oval" />

            {/* Scan line inside oval */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="relative" style={{ width: '70%', aspectRatio: '3/4' }}>
                <div className="scan-line absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-skin-a2 to-transparent opacity-80" />
              </div>
            </div>

            {/* Corner brackets */}
            {[['top-[11%] left-[13%]','border-t-2 border-l-2'],
              ['top-[11%] right-[13%]','border-t-2 border-r-2'],
              ['bottom-[11%] left-[13%]','border-b-2 border-l-2'],
              ['bottom-[11%] right-[13%]','border-b-2 border-r-2']
            ].map(([pos, border], i) => (
              <div key={i} className={`absolute w-6 h-6 ${pos} ${border} border-skin-a2 opacity-90`} />
            ))}

            {/* Flip button */}
            <button onClick={flipCamera}
              className="absolute top-4 left-4 w-10 h-10 rounded-full bg-black/40 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/60 transition-colors">
              <FlipHorizontal size={18} />
            </button>

            {/* Countdown overlay */}
            {camState === 'countdown' && countdown > 0 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="relative flex items-center justify-center">
                  <div className="ripple-ring absolute w-32 h-32 rounded-full border-4 border-skin-a2" />
                  <div className="ripple-ring absolute w-32 h-32 rounded-full border-4 border-skin-a1" style={{ animationDelay: '0.6s' }} />
                  <div className="w-24 h-24 rounded-full bg-black/60 backdrop-blur-md flex items-center justify-center">
                    <span className="font-display text-6xl font-bold text-white leading-none">{countdown}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Status chip */}
            <div className="absolute top-4 right-4 flex items-center gap-1.5 bg-black/50 backdrop-blur-sm rounded-full px-3 py-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400 pulse-dot" />
              <span className="text-white text-xs font-semibold">LIVE</span>
            </div>
          </>
        )}

        {/* Analyzing overlay */}
        {camState === 'capturing' && (
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 rounded-full border-4 border-skin-a1 border-t-skin-a2 animate-spin" />
            <div className="text-center">
              <p className="text-white font-semibold">Analyzing your skin…</p>
              <p className="text-white/60 text-sm mt-1">Running CNN model</p>
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-red-600 text-sm font-medium">{error}</p>
        </div>
      )}

      {/* Action buttons */}
      {(camState === 'live') && (
        <button onClick={beginCapture} disabled={analyzing}
          className="btn-primary w-full flex items-center justify-center gap-3 py-4 text-base anim-fadeup">
          <Zap size={20} />
          Capture & Analyze Skin
        </button>
      )}

      {camState === 'idle' && (
        <div className="text-center text-xs text-skin-muted py-2">
          Camera permission required for live analysis
        </div>
      )}

      {/* Feature chips */}
      <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
        {[
          { icon: '🔬', label: 'CNN Model'     },
          { icon: '⚡', label: 'Instant Scan'  },
          { icon: '🧴', label: 'Routines'      },
        ].map(({ icon, label }) => (
          <div key={label} className="card-soft text-center py-4">
            <p className="text-2xl mb-1">{icon}</p>
            <p className="text-xs font-medium text-skin-muted">{label}</p>
          </div>
        ))}
      </div>

      {/* Privacy */}
      <div className="flex items-center justify-center gap-2 pb-2">
        <ShieldCheck size={13} className="text-skin-muted" />
        <p className="text-xs text-skin-muted">Live frames are analyzed and never stored</p>
      </div>
    </div>
  )
}
