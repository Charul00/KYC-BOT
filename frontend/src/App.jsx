import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import DocumentUpload from './components/DocumentUpload'
import axios from 'axios'

// Uses env var in production (Vercel), falls back to localhost for dev
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default function App() {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState('default')
  const [sessions, setSessions] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => { createNewSession() }, [])

  const createNewSession = async () => {
    try {
      const res = await axios.post(`${API_BASE}/sessions/new`)
      const newId = res.data.session_id
      setSessionId(newId)
      setMessages([])
      setSessions(prev => [...prev, { id: newId, title: 'New Conversation', messages: [] }])
    } catch {
      const fallbackId = Math.random().toString(36).substring(2, 10)
      setSessionId(fallbackId)
      setMessages([])
      setSessions(prev => [...prev, { id: fallbackId, title: 'New Conversation', messages: [] }])
    }
  }

  const switchSession = async (id) => {
    setSessionId(id)
    try {
      const res = await axios.get(`${API_BASE}/sessions/${id}/history`)
      const history = res.data.history || []
      const formatted = []
      history.forEach(ex => {
        formatted.push({ role: 'user', content: ex.human })
        formatted.push({ role: 'assistant', content: ex.ai, sources: [] })
      })
      setMessages(formatted)
    } catch { setMessages([]) }
  }

  const sendMessage = async (query) => {
    if (!query.trim() || isLoading) return
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setIsLoading(true)

    try {
      const res = await axios.post(`${API_BASE}/chat`, { query, session_id: sessionId })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.answer,
        sources: res.data.sources || [],
      }])
    
      setSessions(prev => prev.map(s =>
        s.id === sessionId && s.title === 'New Conversation'
          ? { ...s, title: query.length > 35 ? query.substring(0, 35) + '...' : query }
          : s
      ))
    } catch (err) {
      const status = err.response?.status
      let errorMsg = 'We encountered an issue processing your request. Please try again.'
      if (status === 401) errorMsg = 'Service authentication error. Please contact the administrator.'
      else if (status === 429) errorMsg = 'The service is experiencing high demand. Please wait a moment and try again.'
      else if (status === 503) errorMsg = 'The AI service is temporarily unavailable. Please try again shortly.'

      setMessages(prev => [...prev, { role: 'assistant', content: errorMsg, sources: [], isError: true }])
    } finally { setIsLoading(false) }
  }

  const clearChat = async () => {
    try { await axios.delete(`${API_BASE}/sessions/${sessionId}`) } catch {}
    setMessages([])
  }

  const deleteSession = (id) => {
    setSessions(prev => prev.filter(s => s.id !== id))
    if (id === sessionId) {
      createNewSession()
    }
  }

  return (
    <div className="flex h-screen bg-slate-50">
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

      <div className="flex-1 flex flex-col min-w-0">
        {}
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)} className="p-2 hover:bg-slate-100 rounded-lg">
                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            {/* eClerx Logo + Title */}
            <div className="flex items-center gap-3">
              <img src="/eclerx-logo.svg" alt="eClerx" className="h-7" />
              <div className="w-px h-6 bg-slate-300"></div>
              <span className="text-sm font-semibold text-slate-700">KYC Assistant</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 mr-2">v1.0</span>
            <button onClick={clearChat} className="px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 rounded-lg border border-slate-200">
              Clear Chat
            </button>
          </div>
        </header>

        <ChatWindow messages={messages} isLoading={isLoading} onSendMessage={sendMessage} />
      </div>

      {showUpload && <DocumentUpload onClose={() => setShowUpload(false)} apiBase={API_BASE} />}
    </div>
  )
}
