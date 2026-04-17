import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'

const CATEGORIES = [
  {
    id: 'customer',
    label: 'Customer & KYC',
    color: '#6366f1',
    bg: '#eef2ff',
    border: '#c7d2fe',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    questions: [
      'How many customers have a Verified KYC status?',
      'How many customers are currently Pending KYC review?',
      'How many PEP (Politically Exposed Person) customers are in the database?',
      'Which nationality has the most customers?',
    ],
  },
  {
    id: 'risk',
    label: 'Risk & AML',
    color: '#ef4444',
    bg: '#fef2f2',
    border: '#fecaca',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
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
    color: '#10b981',
    bg: '#ecfdf5',
    border: '#a7f3d0',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
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
    color: '#f59e0b',
    bg: '#fffbeb',
    border: '#fde68a',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    questions: [
      'What documents are required for KYC verification?',
      'What is the process for Enhanced Due Diligence (EDD)?',
      'What are the AML compliance monitoring requirements?',
      'What triggers an AML alert in the system?',
    ],
  },
]

// Animated gradient orb for welcome screen
function GradientOrb() {
  return (
    <div className="relative w-16 h-16 mb-5">
      <div className="orb-glow absolute inset-0 rounded-2xl"
        style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%)' }} />
      <div className="absolute inset-0 rounded-2xl flex items-center justify-center">
        <svg viewBox="0 0 32 32" fill="none" className="w-9 h-9">
          {/* Document */}
          <rect x="6" y="4" width="16" height="20" rx="2" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.8)" strokeWidth="1.5"/>
          <path d="M10 10h8M10 14h8M10 18h5" stroke="rgba(255,255,255,0.9)" strokeWidth="1.5" strokeLinecap="round"/>
          {/* Check badge */}
          <circle cx="22" cy="22" r="6" fill="#10b981"/>
          <path d="M19.5 22l1.5 1.5 3-3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, isLoading, onSendMessage }) {
  const [input, setInput] = useState('')
  const [activeCategory, setActiveCategory] = useState('customer')
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

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

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">

          {messages.length === 0 ? (

            /* ── Welcome screen ── */
            <div className="flex flex-col items-center justify-center min-h-[68vh]">

              <GradientOrb />

              <h2 className="text-[22px] font-bold mb-2 tracking-tight text-slate-800">
                KYC Intelligence Assistant
              </h2>
              <p className="text-slate-500 text-sm text-center max-w-sm leading-relaxed mb-8">
                AI-powered analysis of KYC documents, compliance data &amp; AML monitoring.
                Answers drawn exclusively from your uploaded documents.
              </p>

              {/* Category tabs */}
              <div className="w-full max-w-xl mb-3">
                <p className="text-[10px] uppercase font-bold tracking-widest text-slate-400 mb-2.5">
                  Suggested questions
                </p>
                <div className="flex gap-2 flex-wrap">
                  {CATEGORIES.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setActiveCategory(cat.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border"
                      style={activeCategory === cat.id
                        ? { backgroundColor: cat.color, color: '#fff', borderColor: cat.color, boxShadow: `0 0 0 3px ${cat.color}25` }
                        : { backgroundColor: cat.bg, color: cat.color, borderColor: cat.border }
                      }
                    >
                      {cat.icon}
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question cards */}
              <div className="w-full max-w-xl grid grid-cols-1 sm:grid-cols-2 gap-2">
                {activeGroup.questions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { if (!isLoading) onSendMessage(q) }}
                    disabled={isLoading}
                    className="question-card text-left p-3.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ '--hover-color': activeGroup.color, '--hover-bg': activeGroup.bg }}
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
              <div className="flex flex-wrap gap-2 mt-7 justify-center">
                {[
                  { icon: '📄', label: 'PDF & Word' },
                  { icon: '📊', label: 'Excel & CSV' },
                  { icon: '🖼', label: 'Image & Charts' },
                  { icon: '🔒', label: 'Compliance Docs' },
                ].map(p => (
                  <span key={p.label}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs text-slate-500 font-medium"
                    style={{ backgroundColor: '#f1f5f9' }}>
                    {p.icon} {p.label}
                  </span>
                ))}
              </div>
            </div>

          ) : (
            /* ── Messages ── */
            <>
              {messages.map((msg, idx) => (
                <MessageBubble key={msg.id || idx} message={msg} />
              ))}

              {isLoading && !messages.some(m => m.streaming && m.content?.length > 0) && (
                <div className="flex gap-3 mb-4 message-enter">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-white border border-slate-200 shadow-sm">
                    <BotAvatar size="sm" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                    <div className="flex gap-1.5 items-center">
                      <div className="w-2 h-2 rounded-full typing-dot bg-slate-300" />
                      <div className="w-2 h-2 rounded-full typing-dot bg-slate-300" />
                      <div className="w-2 h-2 rounded-full typing-dot bg-slate-300" />
                      <span className="text-xs text-slate-400 ml-1.5">Searching documents…</span>
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
      <div className="border-t border-slate-200 bg-white px-4 pt-3 pb-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value.slice(0, charLimit))}
                onKeyDown={handleKey}
                placeholder="Ask about KYC status, risk scores, AML alerts, compliance policies…"
                rows={1}
                maxLength={charLimit}
                className="chat-input w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl resize-none text-slate-800 placeholder-slate-400 text-sm"
                style={{ minHeight: '46px', maxHeight: '120px' }}
                disabled={isLoading}
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
              className="send-btn px-4 py-3 text-white rounded-xl disabled:opacity-35 disabled:cursor-not-allowed flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' }}
            >
              {isLoading ? (
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>

          <p className="text-xs text-slate-400 mt-2 text-center">
            <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-mono">Enter</kbd> send
            &nbsp;·&nbsp;
            <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-mono">Shift+Enter</kbd> new line
            &nbsp;·&nbsp; Answers from uploaded documents only
          </p>
        </form>
      </div>
    </div>
  )
}

// Shared bot avatar component (used in typing indicator)
export function BotAvatar({ size = 'md' }) {
  const s = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5'
  return (
    <svg viewBox="0 0 24 24" fill="none" className={s}>
      <rect x="3" y="4" width="12" height="14" rx="1.5" fill="#6366f1" opacity="0.2"
        stroke="#6366f1" strokeWidth="1.4"/>
      <path d="M6 8h6M6 11h6M6 14h4" stroke="#6366f1" strokeWidth="1.3" strokeLinecap="round"/>
      <circle cx="18" cy="17" r="4" fill="#10b981"/>
      <path d="M16 17l1.5 1.5L20 16" stroke="white" strokeWidth="1.3"
        strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
