import React from 'react'

// App logo — pure SVG, no external image dependency
function AppLogo({ size = 36 }) {
  return (
    <div
      className="rounded-xl flex items-center justify-center flex-shrink-0"
      style={{
        width: size, height: size,
        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 60%, #06b6d4 100%)',
      }}
    >
      <svg viewBox="0 0 24 24" fill="none" style={{ width: size * 0.6, height: size * 0.6 }}>
        <rect x="3" y="3" width="11" height="14" rx="1.5"
          fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.85)" strokeWidth="1.4"/>
        <path d="M6 7h5M6 10h5M6 13h3"
          stroke="rgba(255,255,255,0.9)" strokeWidth="1.3" strokeLinecap="round"/>
        <circle cx="18" cy="17" r="4.5" fill="#10b981"/>
        <path d="M15.8 17l1.5 1.5 2.9-2.8"
          stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  )
}

export default function Sidebar({ isOpen, sessions, activeSession, onNewChat, onSelectSession, onDeleteSession, onToggle, onShowUpload }) {
  return (
    <div
      className="flex-shrink-0 h-screen flex flex-col overflow-hidden"
      style={{
        width: isOpen ? '272px' : '0px',
        minWidth: isOpen ? '272px' : '0px',
        transition: 'width 0.26s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.26s cubic-bezier(0.4, 0, 0.2, 1)',
        backgroundColor: '#0f172a',
        overflow: 'hidden',
      }}
    >
      <div className="w-68 flex flex-col h-full" style={{ minWidth: '272px' }}>

        {/* ── Header ── */}
        <div className="px-4 pt-5 pb-4 flex-shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>

          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <AppLogo size={36} />
              <div>
                <p className="text-sm font-bold text-white leading-none">KYC Assistant</p>
                <p className="text-[11px] mt-0.5 font-medium" style={{ color: '#818cf8' }}>
                  AI Compliance Intelligence
                </p>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg transition-all flex-shrink-0"
              style={{ color: '#475569' }}
              onMouseOver={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#94a3b8' }}
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
            className="new-chat-btn w-full px-3 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 text-white transition-all"
            style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            New Conversation
          </button>
        </div>

        {/* ── Sessions ── */}
        <div className="flex-1 overflow-y-auto px-3 py-3 min-h-0">
          <p className="text-[10px] uppercase tracking-widest font-bold mb-2.5 px-2"
            style={{ color: '#1e3a5f' }}>
            Recent
          </p>

          {sessions.length === 0 ? (
            <div className="px-2 py-8 text-center">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                style={{ backgroundColor: 'rgba(99,102,241,0.08)' }}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  style={{ color: '#312e81' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <p className="text-xs font-medium" style={{ color: '#1e3a5f' }}>No conversations yet</p>
              <p className="text-[10px] mt-1" style={{ color: '#0f2340' }}>Start by asking a KYC question</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {[...sessions].reverse().map(session => (
                <div
                  key={session.id}
                  className="group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150"
                  style={{
                    backgroundColor: activeSession === session.id ? 'rgba(99,102,241,0.18)' : 'transparent',
                    color: activeSession === session.id ? '#c7d2fe' : '#475569',
                    borderLeft: `2px solid ${activeSession === session.id ? '#6366f1' : 'transparent'}`,
                  }}
                  onClick={() => onSelectSession(session.id)}
                  onMouseOver={e => {
                    if (activeSession !== session.id) {
                      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'
                      e.currentTarget.style.color = '#64748b'
                    }
                  }}
                  onMouseOut={e => {
                    if (activeSession !== session.id) {
                      e.currentTarget.style.backgroundColor = 'transparent'
                      e.currentTarget.style.color = '#475569'
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
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-lg transition-all flex-shrink-0"
                    onMouseOver={e => e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.2)'}
                    onMouseOut={e => e.currentTarget.style.backgroundColor = 'transparent'}
                    title="Delete"
                  >
                    <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
        <div className="px-3 pb-4 pt-2 flex-shrink-0"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>

          <button
            onClick={onShowUpload}
            className="upload-btn w-full px-3 py-2.5 rounded-xl text-xs font-medium flex items-center gap-2.5 transition-all mb-3"
            style={{ backgroundColor: 'rgba(99,102,241,0.1)', color: '#818cf8' }}
          >
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Upload Documents
          </button>

          {/* Status badge */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="text-[10px] font-medium" style={{ color: '#334155' }}>System Online</span>
            </div>
            <span className="text-[10px]" style={{ color: '#1e293b' }}>v1.0</span>
          </div>
        </div>

      </div>
    </div>
  )
}
