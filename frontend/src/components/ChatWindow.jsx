import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'

// ── KYC-specific suggested questions by category ─────────────────────────────
const CATEGORIES = [
  {
    id: 'customer',
    label: 'Customer & KYC',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    color: '#2563eb',
    bg: '#eff6ff',
    border: '#bfdbfe',
    questions: [
      'How many customers have a Verified KYC status?',
      'How many customers are currently Pending KYC review?',
      'How many PEP (Politically Exposed Person) customers are in the database?',
      'Which nationality has the most customers in the database?',
    ],
  },
  {
    id: 'risk',
    label: 'Risk & AML',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    color: '#dc2626',
    bg: '#fef2f2',
    border: '#fecaca',
    questions: [
      'How many customers are classified as High Risk or Very High Risk?',
      'How many AML alerts are currently Open?',
      'How many SARs (Suspicious Activity Reports) have been filed?',
      'What is the average composite risk score across all assessments?',
    ],
  },
  {
    id: 'transactions',
    label: 'Transactions',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: '#16a34a',
    bg: '#f0fdf4',
    border: '#bbf7d0',
    questions: [
      'What is the total transaction volume in USD?',
      'How many transactions were blocked by compliance?',
      'What was the largest single transaction amount in USD?',
      'What is the average transaction amount in USD?',
    ],
  },
  {
    id: 'policy',
    label: 'Policy & Docs',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    color: '#7c3aed',
    bg: '#faf5ff',
    border: '#e9d5ff',
    questions: [
      'What documents are required for KYC verification?',
      'What is the process for Enhanced Due Diligence (EDD)?',
      'What are the AML compliance monitoring requirements?',
      'What triggers an AML alert in the system?',
    ],
  },
]

// ── KYC Shield icon for welcome hero ──────────────────────────────────────────
function KycShieldIcon() {
  return (
    <svg viewBox="0 0 48 48" fill="none" className="w-10 h-10" xmlns="http://www.w3.org/2000/svg">
      <path d="M24 4L8 11v12c0 9.4 6.8 18.1 16 20.2C33.2 41.1 40 32.4 40 23V11L24 4z"
        fill="#1a2744" />
      <path d="M24 8L12 13.8V23c0 7.6 5.5 14.6 12 16.5 6.5-1.9 12-8.9 12-16.5V13.8L24 8z"
        fill="#2563eb" opacity="0.3"/>
      <path d="M20 24.5l2.5 2.5 5.5-5.5" stroke="white" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

export default function ChatWindow({ messages, isLoading, onSendMessage }) {
  const [input, setInput]               = useState('')
  const [activeCategory, setActiveCategory] = useState('customer')
  const messagesEndRef                  = useRef(null)
  const textareaRef                     = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => { textareaRef.current?.focus() }, [])

  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px'
  }, [input])

  useEffect(() => {
    if (!isLoading) textareaRef.current?.focus()
  }, [isLoading])

  const handleSubmit = (e) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || isLoading) return
    onSendMessage(text)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() }
  }

  const charLimit = 2000
  const charCount = input.length
  const nearLimit = charCount > charLimit * 0.85

  const activeGroup = CATEGORIES.find(c => c.id === activeCategory) || CATEGORIES[0]

  return (
    <div className="flex-1 flex flex-col overflow-hidden">

      {/* ── Messages area ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">

          {messages.length === 0 ? (
            /* ── Welcome screen ── */
            <div className="flex flex-col items-center justify-center min-h-[68vh]">

              {/* Hero */}
              <div className="flex flex-col items-center mb-7">
                <div
                  className="w-20 h-20 rounded-2xl flex items-center justify-center mb-4 shadow-md"
                  style={{ background: 'linear-gradient(135deg, #1a2744 0%, #2563eb 100%)' }}
                >
                  <KycShieldIcon />
                </div>
                <h2 className="text-2xl font-bold mb-1.5 tracking-tight" style={{ color: '#1a2744' }}>
                  KYC Intelligence Assistant
                </h2>
                <p className="text-slate-500 text-sm text-center max-w-sm leading-relaxed">
                  AI-powered assistant for KYC compliance, AML monitoring,
                  risk assessments &amp; customer data — answers only from uploaded documents.
                </p>
              </div>

              {/* ── Category tabs ── */}
              <div className="w-full max-w-xl mb-3">
                <p className="text-[11px] uppercase font-semibold tracking-wider text-slate-400 mb-2 px-0.5">
                  Try asking about
                </p>
                <div className="flex gap-2 flex-wrap">
                  {CATEGORIES.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setActiveCategory(cat.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border"
                      style={activeCategory === cat.id
                        ? { backgroundColor: cat.color, color: '#fff', borderColor: cat.color, boxShadow: `0 2px 8px ${cat.color}40` }
                        : { backgroundColor: cat.bg, color: cat.color, borderColor: cat.border }
                      }
                    >
                      {cat.icon}
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Suggested questions for active category ── */}
              <div className="w-full max-w-xl grid grid-cols-1 sm:grid-cols-2 gap-2">
                {activeGroup.questions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { if (!isLoading) onSendMessage(q) }}
                    disabled={isLoading}
                    className="text-left p-3.5 bg-white border rounded-xl text-sm text-slate-600 transition-all disabled:opacity-40 disabled:cursor-not-allowed group"
                    style={{ borderColor: '#e2e8f0' }}
                    onMouseOver={e => {
                      e.currentTarget.style.borderColor = activeGroup.color
                      e.currentTarget.style.boxShadow = `0 2px 10px ${activeGroup.color}20`
                      e.currentTarget.style.backgroundColor = activeGroup.bg
                    }}
                    onMouseOut={e => {
                      e.currentTarget.style.borderColor = '#e2e8f0'
                      e.currentTarget.style.boxShadow = 'none'
                      e.currentTarget.style.backgroundColor = '#fff'
                    }}
                  >
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 flex-shrink-0" style={{ color: activeGroup.color }}>
                        {activeGroup.icon}
                      </span>
                      <span className="leading-snug">{q}</span>
                    </div>
                  </button>
                ))}
              </div>

              {/* Capability pills */}
              <div className="flex flex-wrap gap-2 mt-6 justify-center">
                {[
                  { icon: '📄', label: 'PDF & Word Docs' },
                  { icon: '📊', label: 'Excel Data' },
                  { icon: '🖼', label: 'Image Analysis' },
                  { icon: '🔒', label: 'Compliance Rules' },
                ].map(p => (
                  <span key={p.label} className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-full text-xs text-slate-500 font-medium">
                    {p.icon} {p.label}
                  </span>
                ))}
              </div>
            </div>

          ) : (
            /* ── Message list ── */
            <>
              {messages.map((msg, idx) => (
                <MessageBubble key={msg.id || idx} message={msg} />
              ))}

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
                      <span className="text-xs text-slate-400 ml-1">Searching KYC documents…</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input area ── */}
      <div className="border-t border-slate-200 bg-white px-4 pt-3 pb-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value.slice(0, charLimit))}
                onKeyDown={handleKey}
                placeholder="Ask about KYC status, risk scores, AML alerts, compliance policies…"
                rows={1}
                maxLength={charLimit}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:border-transparent text-slate-800 placeholder-slate-400 text-sm transition-all"
                style={{ minHeight: '46px', maxHeight: '120px', focusRingColor: '#2563eb' }}
                disabled={isLoading}
                onFocus={e => { e.target.style.borderColor = '#2563eb'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.1)' }}
                onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.boxShadow = 'none' }}
              />
              {nearLimit && (
                <span className="absolute bottom-2 right-3 text-xs"
                  style={{ color: charCount >= charLimit ? '#ef4444' : '#f59e0b' }}>
                  {charLimit - charCount}
                </span>
              )}
            </div>

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
            &nbsp;·&nbsp; Answers from uploaded documents only
          </p>
        </form>
      </div>
    </div>
  )
}
