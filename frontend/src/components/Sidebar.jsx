import React from 'react'

export default function Sidebar({ isOpen, sessions, activeSession, onNewChat, onSelectSession, onDeleteSession, onToggle, onShowUpload }) {
  return (
    <div
      className="flex-shrink-0 h-screen flex flex-col overflow-hidden"
      style={{
        width: isOpen ? '288px' : '0px',
        minWidth: isOpen ? '288px' : '0px',
        transition: 'width 0.28s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.28s cubic-bezier(0.4, 0, 0.2, 1)',
        backgroundColor: '#1a2744',
        overflow: 'hidden',
      }}
    >
      {/* Inner content — fixed width so it doesn't squish during animation */}
      <div className="w-72 flex flex-col h-full" style={{ minWidth: '288px' }}>

        {/* Header */}
        <div className="p-4 border-b flex-shrink-0" style={{ borderColor: '#2a3a5c' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-white flex-shrink-0">
                <img src="/logo_e.png" alt="eClerx" className="h-4" onError={e => { e.target.style.display='none' }} />
              </div>
              <div>
                <span className="font-bold text-white text-sm">eClerx</span>
                <span className="text-xs text-blue-300 block" style={{ marginTop: '-2px' }}>KYC Assistant</span>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors flex-shrink-0"
              style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              title="Close sidebar"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <button
            onClick={onNewChat}
            className="w-full px-3 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 text-white transition-colors"
            style={{ backgroundColor: '#2563eb' }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = '#1d4ed8'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = '#2563eb'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Conversation
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-3 min-h-0">
          <p className="text-xs uppercase tracking-wider mb-3 px-2 font-semibold" style={{ color: '#6b7fa3' }}>
            Recent
          </p>

          {sessions.length === 0 ? (
            <div className="px-2 py-6 text-center">
              <svg className="w-8 h-8 mx-auto mb-2 opacity-20" fill="none" stroke="white" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p className="text-xs" style={{ color: '#4a5f82' }}>No conversations yet</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {[...sessions].reverse().map(session => (
                <div
                  key={session.id}
                  className="group flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-all duration-150"
                  style={{
                    backgroundColor: activeSession === session.id ? 'rgba(37,99,235,0.25)' : 'transparent',
                    color: activeSession === session.id ? '#fff' : '#94a3c3',
                    borderLeft: activeSession === session.id ? '2px solid #3b82f6' : '2px solid transparent',
                  }}
                  onClick={() => onSelectSession(session.id)}
                  onMouseOver={e => { if (activeSession !== session.id) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.06)' }}
                  onMouseOut={e => { if (activeSession !== session.id) e.currentTarget.style.backgroundColor = 'transparent' }}
                >
                  <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span className="truncate flex-1 text-xs leading-snug">{session.title}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id) }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 transition-all duration-150 flex-shrink-0"
                    title="Delete conversation"
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
        <div className="p-3 border-t flex-shrink-0" style={{ borderColor: '#2a3a5c' }}>
          <button
            onClick={onShowUpload}
            className="w-full px-3 py-2.5 rounded-lg text-sm flex items-center gap-2 transition-colors"
            style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: '#94a3c3' }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Upload Documents
          </button>
          <p className="text-center mt-3 text-xs" style={{ color: '#4a5f82' }}>v1.0</p>
        </div>

      </div>
    </div>
  )
}
