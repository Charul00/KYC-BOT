import React, { useState } from 'react'

// ── Copy to clipboard helper
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }
  return (
    <button
      onClick={copy}
      title="Copy to clipboard"
      className="copy-btn opacity-0 group-hover:opacity-100 p-1.5 rounded-lg transition-all hover:bg-slate-100"
      style={{ color: copied ? '#16a34a' : '#94a3b8' }}
    >
      {copied ? (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  )
}

export default function MessageBubble({ message }) {
  const [showSources, setShowSources] = useState(false)
  const isUser     = message.role === 'user'
  const isError    = message.isError
  const isStreaming = message.streaming === true   // actively receiving tokens

  return (
    <div className={`flex gap-3 mb-4 message-enter group ${isUser ? 'flex-row-reverse' : ''}`}>

      {/* Avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
        style={{
          backgroundColor: isUser ? '#2563eb' : isError ? '#fef2f2' : '#ffffff',
          border: isUser ? 'none' : isError ? '1px solid #fecaca' : '1px solid #e2e8f0',
        }}
      >
        {isUser ? (
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        ) : isError ? (
          <span className="text-xs font-bold" style={{ color: '#dc2626' }}>!</span>
        ) : (
          <img src="/eclerx-logo.svg" alt="" className="h-3.5" />
        )}
      </div>

      {/* Content */}
      <div className={`max-w-[80%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>

        {/* Label row */}
        <div className={`flex items-center gap-2 mb-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <p className="text-xs font-medium" style={{ color: '#64748b' }}>
            {isUser ? 'You' : 'eClerx KYC Assistant'}
          </p>
          {/* Copy button — only when AI message is complete */}
          {!isUser && !isError && !isStreaming && message.content && (
            <CopyButton text={message.content} />
          )}
        </div>

        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'rounded-tr-sm text-white'
              : isError
              ? 'bg-red-50 border border-red-200 text-red-700 rounded-tl-sm'
              : 'bg-white border border-slate-200 text-slate-700 rounded-tl-sm'
          }`}
          style={isUser ? { backgroundColor: '#2563eb' } : {}}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
            {/* Real streaming cursor — shown while tokens are actively arriving */}
            {!isUser && !isError && isStreaming && (
              <span className="typing-cursor">▍</span>
            )}
          </p>
        </div>

        {/* Sources — only shown after streaming is complete */}
        {!isUser && !isError && !isStreaming && message.sources && message.sources.length > 0 && (
          <div className="mt-1.5">
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-xs flex items-center gap-1 transition-colors"
              style={{ color: '#2563eb' }}
            >
              <svg
                className={`w-3 h-3 transition-transform ${showSources ? 'rotate-90' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              {message.sources.length} source{message.sources.length > 1 ? 's' : ''} referenced
            </button>

            {showSources && (
              <div className="mt-2 space-y-1.5">
                {message.sources.map((src, idx) => (
                  <div key={idx} className="bg-slate-50 border border-slate-100 rounded-lg p-2.5 text-xs">
                    <div className="flex items-center gap-1.5 mb-1">
                      <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="font-medium text-slate-500">{src.metadata?.source || 'Document'}</span>
                    </div>
                    <p className="text-slate-400 line-clamp-2">{src.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
