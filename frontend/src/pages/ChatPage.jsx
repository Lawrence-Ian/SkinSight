// src/pages/ChatPage.jsx
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, RotateCcw, Sparkles, History, Trash2, Menu, X } from 'lucide-react'
import { chatAPI } from '../utils/api'

const QUICK = ['How to treat acne?','Best sunscreen tips','What is retinol?','Night skincare routine','Foods for healthy skin','How does the camera scan work?']

const INIT = [{
  id: 1, role:'bot',
  text:"Hi! 🌸 I'm **Sage**, your SKINSIGHT skincare assistant.\n\nAsk me anything about skincare, or head to the **Scan** tab to analyze your skin live with the camera!",
  time: new Date()
}]

const fmt = t => t.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br/>')
const toMessages = messages => messages.map(message => ({
  id: message.id,
  role: message.sender === 'user' ? 'user' : 'bot',
  text: message.content,
  time: new Date(message.created_at),
}))

export default function ChatPage() {
  const navigate = useNavigate()
  const [msgs, setMsgs]       = useState(INIT)
  const [sessionId, setSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const [openingSessionId, setOpeningSessionId] = useState(null)
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const bottomRef = useRef()
  const inputRef  = useRef()

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }) }, [msgs])

  useEffect(() => {
    let active = true
    const restore = async () => {
      const savedSessionId = sessionStorage.getItem('sk_chat_session_id')
      try {
        const sessionsResponse = await chatAPI.listSessions()
        if (!active) return
        setSessions(sessionsResponse.data.sessions)
        setHistoryError('')

        if (!savedSessionId) return
        const response = await chatAPI.getSession(savedSessionId)
        if (!active) return
        setSessionId(Number(savedSessionId))
        setMsgs(toMessages(response.data.messages))
      } catch (error) {
        if (error.response?.status === 404) {
          sessionStorage.removeItem('sk_chat_session_id')
          setSessions(current => current.filter(session => String(session.id) !== savedSessionId))
        } else {
          console.error('Could not restore the active chat session:', error)
          setHistoryError('Could not load chat history.')
        }
      } finally {
        if (active) setHistoryLoading(false)
      }
    }
    restore()
    return () => { active = false }
  }, [])

  const openSession = async id => {
    setOpeningSessionId(id)
    try {
      const response = await chatAPI.getSession(id)
      setSessionId(id)
      sessionStorage.setItem('sk_chat_session_id', String(id))
      setMsgs(toMessages(response.data.messages))
      setHistoryError('')
      setHistoryOpen(false)
    } catch (error) {
      console.error('Could not open the selected chat session:', error)
      setHistoryError('Could not open that conversation. Please try again.')
    } finally {
      setOpeningSessionId(null)
    }
  }

  const deleteSession = async id => {
    const session = sessions.find(item => item.id === id)
    const title = session?.title || 'this conversation'
    if (!window.confirm(`Delete ${title}? This cannot be undone.`)) return

    try {
      await chatAPI.deleteSession(id)
      setSessions(current => current.filter(item => item.id !== id))
      if (id === sessionId) startNewChat()
      setHistoryError('')
    } catch (error) {
      console.error('Could not delete the selected chat session:', error)
      setHistoryError('Could not delete that conversation. Please try again.')
    }
  }

  const startNewChat = () => {
    setMsgs(INIT)
    setSessionId(null)
    sessionStorage.removeItem('sk_chat_session_id')
    setHistoryOpen(false)
  }

  const send = async (text) => {
    const m = text || input.trim()
    if (!m || loading) return
    setInput('')
    setMsgs(p => [...p, { id: Date.now(), role:'user', text: m, time: new Date() }])
    setLoading(true)
    try {
      const r = await chatAPI.message(m, sessionId)
      setSessionId(r.data.session_id)
      sessionStorage.setItem('sk_chat_session_id', String(r.data.session_id))
      setMsgs(p => [...p, { id: Date.now()+1, role:'bot', text: r.data.response, time: new Date() }])
      try {
        const sessionsResponse = await chatAPI.listSessions()
        setSessions(sessionsResponse.data.sessions)
      } catch (error) {
        console.error('Could not refresh chat history:', error)
      }
      if (r.data.response.includes('MAP ACTIVATED')) {
        navigate('/map')
      }
    } catch {
      setMsgs(p => [...p, { id: Date.now()+1, role:'bot', text:"Connection issue 😓 Please try again.", time: new Date() }])
    } finally { setLoading(false); inputRef.current?.focus() }
  }

  return (
    <div className="chat-page">
      {historyOpen && <button className="chat-history-backdrop" aria-label="Close chat history" onClick={() => setHistoryOpen(false)} />}
      <aside className={`chat-history-panel ${historyOpen ? 'is-open' : ''}`} aria-hidden={!historyOpen}>
        <div className="chat-history-header">
          <div className="flex items-center gap-2">
            <History size={15} className="text-skin-a2" />
            <h2 className="text-sm font-semibold text-skin-text">Chat history</h2>
          </div>
          <div className="chat-history-actions">
            <button onClick={startNewChat} className="text-xs font-medium text-skin-a2 hover:text-skin-text transition-colors">New chat</button>
            <button className="chat-history-close" aria-label="Close chat history" onClick={() => setHistoryOpen(false)}><X size={16} /></button>
          </div>
        </div>
        {historyError && <p className="px-2 py-2 text-xs text-red-500">{historyError}</p>}
        {historyLoading ? (
          <p className="px-2 py-3 text-xs text-skin-muted">Loading conversations...</p>
        ) : sessions.length === 0 ? (
          <p className="px-2 py-3 text-xs text-skin-muted">Your saved conversations will appear here.</p>
        ) : (
          <div className="chat-history-list">
            {sessions.map(session => (
              <div key={session.id}
                className={`chat-history-item ${
                  session.id === sessionId
                    ? 'bg-skin-a1/30'
                    : 'hover:bg-skin-a1/15'
                }`}>
                <button onClick={() => openSession(session.id)}
                  disabled={openingSessionId === session.id}
                  className={`chat-history-session min-w-0 flex-1 rounded-xl px-3 py-2 text-left text-skin-muted hover:text-skin-text ${
                    session.id === sessionId ? 'text-skin-text' : ''
                  }`}>
                  <span className="block truncate text-xs font-medium">
                    {openingSessionId === session.id ? 'Opening...' : session.title || 'Untitled conversation'}
                  </span>
                  <span className="block mt-0.5 text-[10px] opacity-70">
                    {new Date(session.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </span>
                </button>
                <button className="chat-history-delete" onClick={() => deleteSession(session.id)}
                  aria-label={`Delete ${session.title || 'conversation'}`}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </aside>

      <section className="chat-conversation">
      {/* Chat header */}
      <div className="px-4 sm:px-5 py-3 border-b border-skin-border flex items-center justify-between bg-skin-bg gap-2">
        <div className="flex items-center gap-3">
          <button className="chat-history-toggle" aria-label="Open chat history" aria-expanded={historyOpen} onClick={() => setHistoryOpen(true)}>
            <Menu size={20} />
          </button>
          <div className="w-10 h-10 rounded-2xl bg-skin-a1/40 flex items-center justify-center">
            <Sparkles size={17} className="text-skin-a2" />
          </div>
          <div>
            <p className="font-semibold text-skin-text">Sage</p>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <p className="text-xs text-skin-muted">Skincare AI Assistant</p>
            </div>
          </div>
        </div>
        <button onClick={startNewChat}
          className="w-9 h-9 rounded-xl bg-skin-card border border-skin-border flex items-center justify-center hover:bg-skin-a1/30 transition-colors">
          <RotateCcw size={14} className="text-skin-muted" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-5 py-3.5 flex flex-col gap-4">
        {msgs.map(msg => (
          <div key={msg.id} className={`flex flex-col gap-1 anim-fadeup ${msg.role==='user' ? 'items-end' : 'items-start'}`}>
            {msg.role==='bot' && (
              <div className="flex items-center gap-1.5 mb-0.5">
                <div className="w-5 h-5 rounded-full bg-skin-a1/40 flex items-center justify-center">
                  <Sparkles size={10} className="text-skin-a2" />
                </div>
                <span className="text-xs font-medium text-skin-muted">Sage</span>
              </div>
            )}
            <div className={msg.role==='user' ? 'bubble-user' : 'bubble-bot'}
              dangerouslySetInnerHTML={{ __html: fmt(msg.text) }} />
            <p className="text-[10px] text-skin-muted px-1">
              {msg.time.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}
            </p>
          </div>
        ))}

        {loading && (
          <div className="flex items-start gap-2 anim-fadein">
            <div className="w-5 h-5 rounded-full bg-skin-a1/40 flex items-center justify-center mt-0.5">
              <Sparkles size={10} className="text-skin-a2" />
            </div>
            <div className="bubble-bot flex items-center gap-1.5">
              {[0,150,300].map(d => (
                <div key={d} className="w-2 h-2 rounded-full bg-skin-muted animate-bounce" style={{ animationDelay:`${d}ms` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      {msgs.length <= 2 && (
        <div className="chat-quick-prompts px-4 sm:px-5 pb-2">
          <p className="text-xs text-skin-muted mb-2 font-medium">Quick questions:</p>
          <div className="chat-quick-scroll flex gap-1.5">
            {QUICK.map(q => (
              <button key={q} onClick={() => send(q)}
                className="chat-quick-button text-xs px-2.5 sm:px-3 py-1.5 rounded-full bg-skin-card border border-skin-border text-skin-muted hover:border-skin-a2 hover:text-skin-a2 transition-all">
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-4 sm:px-5 pt-2 border-t border-skin-border bg-skin-bg pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <div className="flex items-end gap-2.5 bg-white rounded-2xl border border-skin-border px-4 py-2.5 shadow-sm">
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()} }}
            onInput={e => { e.target.style.height='auto'; e.target.style.height=Math.min(e.target.scrollHeight,96)+'px' }}
            placeholder="Ask about skincare…" rows={1}
            className="flex-1 bg-transparent text-sm text-skin-text placeholder-skin-muted resize-none outline-none leading-relaxed" />
          <button onClick={() => send()} disabled={!input.trim()||loading}
            className="w-9 h-9 rounded-xl bg-skin-a2 flex items-center justify-center text-white disabled:opacity-40 hover:opacity-90 active:scale-95 transition-all flex-shrink-0">
            <Send size={15} />
          </button>
        </div>
        <p className="text-center text-[10px] text-skin-muted mt-1.5">Not a substitute for medical advice</p>
      </div>
      </section>
    </div>
  )
}
