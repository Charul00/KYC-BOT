import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'

export default function ChatWindow({ messages, isLoading, onSendMessage }) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isLoading])
  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim()) { onSendMessage(input.trim()); setInput('') }
  }

  const suggestedQuestions = [
    "What is eClerx and what do they do?",
    "Where are eClerx's offices located globally?",
    "What compliance certifications does eClerx hold?",
    "What are eClerx's key products and platforms?",
  ]

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[65vh]">
              {/* eClerx Logo */}
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5 bg-white shadow-sm border border-slate-100">
                <img src="/eclerx-logo.svg" alt="eClerx" className="h-6" />
              </div>
              <h2 className="text-xl font-bold mb-2" style={{ color: '#1a2744' }}>eClerx KYC Assistant</h2>
              <p className="text-slate-500 mb-8 text-center max-w-sm text-sm">
                Ask me anything about the uploaded KYC documents. I'm here to help you find the information you need.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => onSendMessage(q)}
                    className="text-left p-3 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-sm text-sm text-slate-600 transition-all"
                  >
                    <span className="text-blue-500 mr-1.5">&#8250;</span>{q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => <MessageBubble key={idx} message={msg} />)}
              {isLoading && (
                <div className="flex gap-3 mb-4 message-enter">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-white border border-slate-200">
                    <img src="/eclerx-logo.svg" alt="" className="h-3.5" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 rounded-full typing-dot" style={{ backgroundColor: '#94a3b8' }}></div>
                      <div className="w-2 h-2 rounded-full typing-dot" style={{ backgroundColor: '#94a3b8' }}></div>
                      <div className="w-2 h-2 rounded-full typing-dot" style={{ backgroundColor: '#94a3b8' }}></div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) } }}
                placeholder="Ask a question about KYC documents..."
                rows={1}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 placeholder-slate-400 text-sm"
                style={{ minHeight: '46px', maxHeight: '120px' }}
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
              style={{ backgroundColor: '#2563eb' }}
              onMouseOver={e => { if (!e.target.disabled) e.target.style.backgroundColor = '#1d4ed8' }}
              onMouseOut={e => e.target.style.backgroundColor = '#2563eb'}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2 text-center">
            Press Enter to send &middot; Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  )
}
