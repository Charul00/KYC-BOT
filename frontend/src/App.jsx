import React, { useState, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import DocumentUpload from './components/DocumentUpload'
import axios from 'axios'

// Uses env var in production (Vercel), falls back to localhost for dev
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default function App() {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const initDone = useRef(false)

  useEffect(() => {
    if (!initDone.current) {
      initDone.current = true
      createNewSession()
    }
  }, [])

  // ─── FIX: Generate session ID locally FIRST, then sync with backend
  // This prevents the race condition where a slow Render cold-start response
  // would call setMessages([]) after the user already typed something.
  const createNewSession = async () => {
    // 1. Generate local ID immediately — don't wait for backend
    const localId = 'sess_' + Math.random().toString(36).substring(2, 10)
    setSessionId(localId)
    setMessages([])
    const newSession = { id: localId, title: 'New Conversation' }
    setSessions(prev => [...prev, newSession])

    // 2. Try to register session with backend in background
    try {
      const res = await axios.post(`${API_BASE}/sessions/new`, {}, { timeout: 15000 })
      const backendId = res.data.session_id
      if (backendId) {
        // Swap the local ID for the backend-assigned ID — but only if user hasn't typed yet
        setSessionId(prev => (prev === localId ? backendId : prev))
        setSessions(prev =>
          prev.map(s => (s.id === localId ? { ...s, id: backendId } : s))
        )
      }
    } catch {
      // Backend is waking up (cold start) — that's fine, the local ID still works for chat
    }
  }

  const switchSession = async (id) => {
    setSessionId(id)
    try {
      const res = await axios.get(`${API_BASE}/sessions/${id}/history`, { timeout: 10000 })
      const history = res.data.history || []
      const formatted = []
      history.forEach(ex => {
        formatted.push({ role: 'user', content: ex.human, timestamp: new Date().toISOString() })
        formatted.push({ role: 'assistant', content: ex.ai, sources: [], timestamp: new Date().toISOString() })
      })
      setMessages(formatted)
    } catch {
      setMessages([])
    }
  }

  const sendMessage = async (query) => {
    if (!query.trim() || isLoading) return

    const userMsg = { role: 'user', content: query, timestamp: new Date().toISOString() }
    // Unique ID so we can update the streaming message in-place
    const aiMsgId = `ai_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`

    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    // Update session title from first message
    setSessions(prev =>
      prev.map(s =>
        s.id === sessionId && s.title === 'New Conversation'
          ? { ...s, title: query.length > 40 ? query.substring(0, 40) + '…' : query }
          : s
      )
    )

    // Add an empty placeholder AI message that we'll stream into
    setMessages(prev => [
      ...prev,
      { id: aiMsgId, role: 'assistant', content: '', sources: [], streaming: true, timestamp: new Date().toISOString() },
    ])

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
        signal: AbortSignal.timeout(90000),   // 90s hard timeout
      })

      if (!response.ok) {
        const status = response.status
        let errorMsg = 'Something went wrong. Please try again.'
        if (status === 401) errorMsg = 'Authentication error. Please contact the administrator.'
        else if (status === 429) errorMsg = 'Service is busy right now. Please wait a moment and try again.'
        else if (status === 503) errorMsg = 'The AI model is temporarily unavailable. Please try again shortly.'
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgId
              ? { ...m, content: errorMsg, isError: true, streaming: false }
              : m
          )
        )
        setIsLoading(false)
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE lines are separated by \n\n
        const parts = buffer.split('\n\n')
        buffer = parts.pop()  // keep incomplete chunk

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.done) {
              // Stream complete — attach sources and mark done
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
                prev.map(m =>
                  m.id === aiMsgId ? { ...m, content: accumulated } : m
                )
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
        prev.map(m =>
          m.id === aiMsgId
            ? { ...m, content: errorMsg, isError: true, streaming: false }
            : m
        )
      )
      setIsLoading(false)
    }
  }

  const clearChat = async () => {
    try { await axios.delete(`${API_BASE}/sessions/${sessionId}`) } catch {}
    setMessages([])
  }

  const deleteSession = async (id) => {
    try { await axios.delete(`${API_BASE}/sessions/${id}`) } catch {}
    setSessions(prev => prev.filter(s => s.id !== id))
    if (id === sessionId) createNewSession()
  }

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      <Sidebar
        isOpen={sidebarOpen}
        sessions={sessions}
        activeSession={sessionId}
        onNewChat={createNewSession}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onShowUpload={() => setShowUpload(true)}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header bar */}
        <header className="bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between flex-shrink-0 shadow-sm">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            <div className="flex items-center gap-3">
              <img src="/eclerx-logo.svg" alt="eClerx" className="h-7" />
              <div className="w-px h-5 bg-slate-200" />
              <div>
                <p className="text-sm font-semibold text-slate-800 leading-none">KYC Assistant</p>
                <p className="text-xs text-slate-400 mt-0.5">Powered by GPT-4o · RAG</p>
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

      {showUpload && (
        <DocumentUpload
          onClose={() => setShowUpload(false)}
          apiBase={API_BASE}
        />
      )}
    </div>
  )
}
