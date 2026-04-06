import React from 'react'

export default function Sidebar({ isOpen, sessions, activeSession, onNewChat, onSelectSession, onDeleteSession, onToggle, onShowUpload }) {
  return (
    <div
      className="flex-shrink-0 h-screen flex flex-col overflow-hidden"
      style={{
        width: isOpen ? '288px' : '0px',
        minWidth: isOpen ? '288px' : '0px',
        transition: 'width 0.28s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.28s cubic-bezier(0.4, 0, 0.2, 1)',
        backgroundColor: '#0f1a2e',
        overflow: 'hidden',
      }}
    >
      <div className="w-72 flex flex-col h-full" style={{ minWidth: '288px' }}>

        {/* ── Header ── */}
        <div className="p-4 flex-shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              {/* Logo mark */}
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: '#ffffff' }}
              >
                <img src="/logo_e.png" alt="Logo" className="h-6 w-auto object-contain" />
              </div>
              <div>
                <span className="font-bold text-white text-sm leading-none">eClerx</span>
                <span className="text-[11px] block mt-0.5 font-medium" style={{ color: '#60a5fa' }}>
                  KYC Assistant
                </span>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg transition-colors flex-shrink-0"
              style={{ color: '#475569' }}
              onMouseOver={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = '#fff' }}
              onMouseOut={e => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = '#475569' }}
              title="Close sidebar"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <button
            onClick={onNewChat}
            className="w-full px-3 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 text-white transition-all"
            style={{ background: 'linear-gradient(135deg, #2563eb, #1d4ed8)' }}
            onMouseOver={e => e.currentTarget.style.opacity = '0.9'}
            onMouseOut={e => e.currentTarget.style.opacity = '1'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            New Conversation
          </button>
        </div>

        {/* ── Sessions list ── */}
        <div className="flex-1 overflow-y-auto p-3 min-h-0">
          <p className="text-[10px] uppercase tracking-widest mb-2.5 px-2 font-bold" style={{ color: '#334155' }}>
            Recent
          </p>

          {sessions.length === 0 ? (
            <div className="px-2 py-8 text-center">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-2.5"
                style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  style={{ color: '#334155' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <p className="text-xs" style={{ color: '#334155' }}>No conversations yet</p>
              <p className="text-[10px] mt-0.5" style={{ color: '#1e293b' }}>
                Start by asking a KYC question
              </p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {[...sessions].reverse().map(session => (
                <div
                  key={session.id}
                  className="group flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm cursor-pointer transition-all duration-150"
                  style={{
                    backgroundColor: activeSession === session.id
                      ? 'rgba(37,99,235,0.2)'
                      : 'transparent',
                    color: activeSession === session.id ? '#fff' : '#64748b',
                    borderLeft: activeSession === session.id
                      ? '2px solid #3b82f6'
                      : '2px solid transparent',
                  }}
                  onClick={() => onSelectSession(session.id)}
                  onMouseOver={e => {
                    if (activeSession !== session.id) {
                      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'
                      e.currentTarget.style.color = '#94a3b8'
                    }
                  }}
                  onMouseOut={e => {
                    if (activeSession !== session.id) {
                      e.currentTarget.style.backgroundColor = 'transparent'
                      e.currentTarget.style.color = '#64748b'
                    }
                  }}
                >
                  <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span className="truncate flex-1 text-xs leading-snug">{session.title}</span>
                  <button
                    onClick={e => { e.stopPropagation(); onDeleteSession(session.id) }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-lg transition-all duration-150 flex-shrink-0"
                    onMouseOver={e => e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.2)'}
                    onMouseOut={e => e.currentTarget.style.backgroundColor = 'transparent'}
                    title="Delete conversation"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      style={{ color: '#f87171' }}>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="p-3 flex-shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          {/* Upload button */}
          <button
            onClick={onShowUpload}
            className="w-full px-3 py-2.5 rounded-xl text-sm flex items-center gap-2.5 transition-all mb-2"
            style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: '#64748b' }}
            onMouseOver={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.09)'; e.currentTarget.style.color = '#94a3b8' }}
            onMouseOut={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#64748b' }}
          >
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <span className="text-xs font-medium">Upload Documents</span>
          </button>

          {/* Compliance badge */}
          <div
            className="flex items-center justify-center gap-1.5 py-2 rounded-xl"
            style={{ backgroundColor: 'rgba(255,255,255,0.03)' }}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"
              style={{ color: '#22c55e' }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-[10px] font-medium" style={{ color: '#334155' }}>
              AML/KYC Compliant · v1.0
            </span>
          </div>
        </div>

      </div>
    </div>
  )
}
