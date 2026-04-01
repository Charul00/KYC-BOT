import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'

const SUGGESTED = [
  "What is eClerx and what do they do?",
  "Where are eClerx's offices located globally?",
  "What compliance certifications does eClerx hold?",
  "What are eClerx's key products and platforms?",
]

export default function ChatWindow({ messages, isLoading, onSendMessage, isStreaming }) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Auto-focus on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  // Auto-resize textarea as user types
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px'
  }, [input])

  // Re-focus after message is sent (when isLoading becomes false)
  useEffect(() => {
    if (!isLoading) textareaRef.current?.focus()
  }, [isLoading])

  const handleSubmit = (e) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || isLoading) return
    onSendMessage(text)
    setInput('')
    // Reset height
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const charCount = input.length
  const charLimit = 1500
  const nearLimit = charCount > charLimit * 0.85

  return (
    <div className="flex-1 flex flex-col overflow-hidden">

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">

          {messages.length === 0 ? (
            /* Welcome screen */
            <div className="flex flex-col items-center justify-center min-h-[65vh]">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5 bg-white shadow-sm border border-slate-100">
                <img src="/eclerx-logo.svg" alt="eClerx" className="h-6" />
              </div>
              <h2 className="text-xl font-bold mb-2" style={{ color: '#1a2744' }}>eClerx KYC Assistant</h2>
              <p className="text-slate-500 mb-8 text-center max-w-sm text-sm">
                Ask me anything about the uploaded KYC documents. I answer only from the documents — no guessing.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
                {SUGGESTED.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { if (!isLoading) onSendMessage(q) }}
                    disabled={isLoading}
                    className="text-left p-3 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-sm hover:bg-blue-50 text-sm text-slate-600 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <span className="text-blue-500 mr-1.5">›</span>{q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <MessageBubble
                  key={msg.id || idx}
                  message={msg}
                />
              ))}

              {/*
                Typing indicator — shown only while waiting for FIRST token.
                Once streaming starts (the AI bubble has content), hide it.
                This prevents a flash of both the indicator and the bubble.
              */}
              {isLoading && !messages.some(m => m.streaming && m.content && m.content.length > 0) && (
                <div className="flex gap-3 mb-4 message-enter">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-white border border-slate-200">
                    <img src="/eclerx-logo.svg" alt="" className="h-3.5" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex gap-1.5 items-center">
                      <div className="w-2 h-2 rounded-full typing-dot" style={{ backgroundColor: '#94a3b8' }} />
                      <div className="w-2 h-2 rounded-full typing-dot" style={{ backgroundColor: '#94a3b8' }} />
                      <div className="w-2 h-2 rounded-full typing-dot" style={{ backgroundColor: '#94a3b8' }} />
                      <span className="text-xs text-slate-400 ml-1">Searching documents…</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input ── */}
      <div className="border-t border-slate-200 bg-white p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value.slice(0, charLimit))}
                onKeyDown={handleKey}
                placeholder="Ask a question about KYC documents…"
                rows={1}
                maxLength={charLimit}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 placeholder-slate-400 text-sm transition-all"
                style={{ minHeight: '46px', maxHeight: '120px' }}
                disabled={isLoading}
              />
              {/* Character counter — only shown when near limit */}
              {nearLimit && (
                <span
                  className="absolute bottom-2 right-3 text-xs"
                  style={{ color: charCount >= charLimit ? '#ef4444' : '#f59e0b' }}
                >
                  {charLimit - charCount}
                </span>
              )}
            </div>

            {/* Send button */}
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all flex-shrink-0 active:scale-95"
              style={{ backgroundColor: '#2563eb' }}
              onMouseOver={e => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = '#1d4ed8' }}
              onMouseOut={e => { e.currentTarget.style.backgroundColor = '#2563eb' }}
            >
              {isLoading ? (
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>

          <p className="text-xs text-slate-400 mt-2 text-center">
            <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-xs font-mono">Enter</kbd> to send
            &nbsp;·&nbsp;
            <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-xs font-mono">Shift+Enter</kbd> for new line
            &nbsp;·&nbsp; Answers from documents only
          </p>
        </form>
      </div>
    </div>
  )
}
