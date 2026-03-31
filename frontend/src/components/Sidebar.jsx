import React from 'react'

export default function Sidebar({ isOpen, sessions, activeSession, onNewChat, onSelectSession, onDeleteSession, onToggle, onShowUpload }) {
  if (!isOpen) return null

  return (
    <div className="w-72 flex flex-col h-screen" style={{ backgroundColor: '#1a2744' }}>
      {/* Header */}
      <div className="p-4 border-b" style={{ borderColor: '#2a3a5c' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-white">
              <img src="/logo_e.png" alt="eClerx" className="h-4" />
            </div>
            <div>
              <span className="font-bold text-white text-sm">eClerx</span>
              <span className="text-xs text-blue-300 block" style={{ marginTop: '-2px' }}>KYC Assistant</span>
            </div>
          </div>
          <button onClick={onToggle} className="p-1.5 rounded-lg text-slate-400 hover:text-white" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <button
          onClick={onNewChat}
          className="w-full px-3 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 text-white transition-colors"
          style={{ backgroundColor: '#2563eb' }}
          onMouseOver={e => e.target.style.backgroundColor = '#1d4ed8'}
          onMouseOut={e => e.target.style.backgroundColor = '#2563eb'}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Conversation
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto p-3">
        <p className="text-xs uppercase tracking-wider mb-3 px-2" style={{ color: '#6b7fa3' }}>Recent</p>
        {sessions.length === 0 ? (
          <p className="text-xs px-2" style={{ color: '#4a5f82' }}>No conversations yet</p>
        ) : (
          <div className="space-y-1">
            {[...sessions].reverse().map(session => (
              <div
                key={session.id}
                className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-all ${
                  activeSession === session.id ? 'text-white' : 'hover:text-white'
                }`}
                style={{
                  backgroundColor: activeSession === session.id ? 'rgba(37,99,235,0.2)' : 'transparent',
                  color: activeSession === session.id ? '#fff' : '#94a3c3',
                }}
                onClick={() => onSelectSession(session.id)}
                onMouseOver={e => { if (activeSession !== session.id) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)' }}
                onMouseOut={e => { if (activeSession !== session.id) e.currentTarget.style.backgroundColor = 'transparent' }}
              >
                <svg className="w-4 h-4 flex-shrink-0 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span className="truncate flex-1 text-xs">{session.title}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id) }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 transition-opacity"
                >
                  <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom */}
      <div className="p-3 border-t" style={{ borderColor: '#2a3a5c' }}>
        <button
          onClick={onShowUpload}
          className="w-full px-3 py-2.5 rounded-lg text-sm flex items-center gap-2 transition-colors"
          style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: '#94a3c3' }}
          onMouseOver={e => e.target.style.backgroundColor = 'rgba(255,255,255,0.1)'}
          onMouseOut={e => e.target.style.backgroundColor = 'rgba(255,255,255,0.05)'}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Upload Documents
        </button>
        <p className="text-center mt-3 text-xs" style={{ color: '#4a5f82' }}>v1.0</p>
      </div>
    </div>
  )
}
