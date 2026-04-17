import React, { useState, useEffect, useRef, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import DocumentUpload from './components/DocumentUpload'
import ProcessingBadge from './components/ProcessingBadge'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
const SESSIONS_KEY = 'kyc_sessions_v1'
const MAX_STORED_SESSIONS = 30

// ── Persist sessions in localStorage ────────────────────────────────────────
function loadSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveSessions(sessions) {
  try {
    // Keep only the most recent MAX_STORED_SESSIONS
    const trimmed = sessions.slice(-MAX_STORED_SESSIONS)
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(trimmed))
  } catch {}
}

export default function App() {
  const [messages, setMessages]       = useState([])
  const [sessionId, setSessionId]     = useState(null)
  const [sessions, setSessions]       = useState(loadSessions)   // init from localStorage
  const [isLoading, setIsLoading]     = useState(false)
  const [showUpload, setShowUpload]   = useState(false)
  const [bgJobs, setBgJobs]           = useState([])   // jobs shared with floating badge
  const handleJobsChange = useCallback((jobs) => setBgJobs(jobs), [])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const initDone = useRef(false)

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    saveSessions(sessions)
  }, [sessions])

  // Create first session on mount
  useEffect(() => {
    if (!initDone.current) {
      initDone.current = true
      createNewSession()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Session management ─────────────────────────────────────────────────────

  const createNewSession = async () => {
    // Generate local ID immediately — don't block on backend
    const localId = 'sess_' + Math.random().toString(36).substring(2, 10)
    setSessionId(localId)
    setMessages([])

    const newSession = { id: localId, title: 'New Conversation', createdAt: Date.now() }
    setSessions(prev => [...prev, newSession])

    // Register with backend in background
    try {
      const res = await axios.post(`${API_BASE}/sessions/new`, {}, { timeout: 15000 })
      const backendId = res.data.session_id
      if (backendId) {
        setSessionId(prev => (prev === localId ? backendId : prev))
        setSessions(prev =>
          prev.map(s => (s.id === localId ? { ...s, id: backendId } : s))
        )
      }
    } catch {
      // Backend cold start — local ID still works for chat
    }
  }

  const switchSession = async (id) => {
    if (id === sessionId) return
    setSessionId(id)
    setMessages([])

    try {
      const res = await axios.get(`${API_BASE}/sessions/${id}/history`, { timeout: 10000 })
      const history = res.data.history || []
      const formatted = []
      history.forEach(ex => {
        formatted.push({ role: 'user',      content: ex.human, timestamp: new Date().toISOString() })
        formatted.push({ role: 'assistant', content: ex.ai,    sources: [], timestamp: new Date().toISOString() })
      })
      setMessages(formatted)
    } catch {
      setMessages([])
    }
  }

  const deleteSession = async (id) => {
    try { await axios.delete(`${API_BASE}/sessions/${id}`) } catch {}
    setSessions(prev => prev.filter(s => s.id !== id))
    if (id === sessionId) createNewSession()
  }

  const clearChat = async () => {
    try { await axios.delete(`${API_BASE}/sessions/${sessionId}`) } catch {}
    setMessages([])
    // Update session title back to default
    setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title: 'New Conversation' } : s))
  }

  // ── Message sending (streaming SSE) ───────────────────────────────────────

  const sendMessage = async (query) => {
    if (!query.trim() || isLoading) return

    const userMsg  = { role: 'user', content: query, timestamp: new Date().toISOString() }
    const aiMsgId  = `ai_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`

    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    // Update session title from the first real message
    setSessions(prev =>
      prev.map(s =>
        s.id === sessionId && s.title === 'New Conversation'
          ? { ...s, title: query.length > 42 ? query.substring(0, 42) + '…' : query }
          : s
      )
    )

    // Add empty streaming placeholder
    setMessages(prev => [
      ...prev,
      { id: aiMsgId, role: 'assistant', content: '', sources: [], streaming: true, timestamp: new Date().toISOString() },
    ])

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
        signal: AbortSignal.timeout(90000),
      })

      if (!response.ok) {
        const status = response.status
        let errorMsg = 'Something went wrong. Please try again.'
        if (status === 401) errorMsg = 'Authentication error. Please contact the administrator.'
        else if (status === 429) errorMsg = 'Service is busy right now. Please wait a moment and try again.'
        else if (status === 503) errorMsg = 'The AI model is temporarily unavailable. Please try again shortly.'
        setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, content: errorMsg, isError: true, streaming: false } : m))
        setIsLoading(false)
        return
      }

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop()

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.done) {
              setMessages(prev =>
                prev.map(m =>
                  m.id === aiMsgId
                    ? { ...m, content: accumulated, sources: data.sources || [], streaming: false }
                    : m
                )
              )
              setIsLoading(false)
            } else if (data.token) {
              accumulated += data.token
              setMessages(prev =>
                prev.map(m => m.id === aiMsgId ? { ...m, content: accumulated } : m)
              )
            }
          } catch {
            // Malformed JSON — skip
          }
        }
      }
    } catch (err) {
      let errorMsg = 'Something went wrong. Please try again.'
      if (err.name === 'TimeoutError') errorMsg = 'Request timed out. The server may be waking up — please try again.'
      else if (err.name === 'AbortError') errorMsg = 'Request was cancelled.'
      setMessages(prev =>
        prev.map(m => m.id === aiMsgId ? { ...m, content: errorMsg, isError: true, streaming: false } : m)
      )
      setIsLoading(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">

      {/* Sidebar — always in DOM, slides in/out via width transition */}
      <Sidebar
        isOpen={sidebarOpen}
        sessions={sessions}
        activeSession={sessionId}
        onNewChat={createNewSession}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
        onToggle={() => setSidebarOpen(o => !o)}
        onShowUpload={() => setShowUpload(true)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Top header */}
        <header className="bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between flex-shrink-0 shadow-sm">
          <div className="flex items-center gap-3">
            {/* Hamburger — only shown when sidebar is closed */}
            <button
              onClick={() => setSidebarOpen(o => !o)}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
              style={{ opacity: sidebarOpen ? 0.4 : 1 }}
            >
              <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div className="flex items-center gap-3">
              {/* App icon — pure SVG, no external image */}
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' }}>
                <svg viewBox="0 0 20 20" fill="none" className="w-5 h-5">
                  <rect x="2" y="2" width="9" height="12" rx="1.2"
                    fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.85)" strokeWidth="1.2"/>
                  <path d="M4.5 6h4M4.5 8.5h4M4.5 11h2.5"
                    stroke="rgba(255,255,255,0.9)" strokeWidth="1.1" strokeLinecap="round"/>
                  <circle cx="15" cy="15" r="4" fill="#10b981"/>
                  <path d="M13.2 15l1.3 1.3L17 13.5"
                    stroke="white" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="w-px h-5 bg-slate-200" />
              <div>
                <p className="text-sm font-semibold text-slate-800 leading-none">KYC Assistant</p>
                <p className="text-xs text-slate-400 mt-0.5">AI Compliance Intelligence</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 mr-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-slate-400">Online</span>
            </div>
            <button
              onClick={clearChat}
              className="px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            >
              Clear Chat
            </button>
          </div>
        </header>

        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSendMessage={sendMessage}
        />
      </div>

      {/* Upload modal — always mounted so background polling survives close */}
      <DocumentUpload
        visible={showUpload}
        onClose={() => setShowUpload(false)}
        apiBase={API_BASE}
        onJobsChange={handleJobsChange}
      />

      {/* Floating processing badge — appears when modal is closed but jobs are running */}
      {!showUpload && (
        <ProcessingBadge
          jobs={bgJobs}
          onReopen={() => setShowUpload(true)}
        />
      )}
    </div>
  )
}
