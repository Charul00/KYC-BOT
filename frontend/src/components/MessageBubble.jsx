import React, { useState } from 'react'

export default function MessageBubble({ message }) {
  const [showSources, setShowSources] = useState(false)
  const isUser = message.role === 'user'
  const isError = message.isError

  return (
    <div className={`flex gap-3 mb-4 message-enter ${isUser ? 'flex-row-reverse' : ''}`}>
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
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Label */}
        <p className={`text-xs font-medium mb-1 ${isUser ? 'text-right' : ''}`} style={{ color: '#64748b' }}>
          {isUser ? 'You' : 'eClerx KYC Assistant'}
        </p>

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
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-1.5">
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-xs flex items-center gap-1 transition-colors"
              style={{ color: '#2563eb' }}
            >
              <svg className={`w-3 h-3 transition-transform ${showSources ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
