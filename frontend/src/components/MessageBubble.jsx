import React, { useState } from 'react'
import { BotAvatar } from './ChatWindow'

// ── Inline markdown renderer ─────────────────────────────────────────────────
function renderInline(text, key = '') {
  if (!text) return null
  const parts = []
  const regex = /(\*\*[^*\n]+\*\*|\*[^*\n]+\*|`[^`\n]+`)/g
  let lastIndex = 0
  let match
  let idx = 0

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index))
    const token = match[0]
    if (token.startsWith('**'))
      parts.push(<strong key={`${key}-b${idx++}`} className="font-semibold text-slate-800">{token.slice(2, -2)}</strong>)
    else if (token.startsWith('*'))
      parts.push(<em key={`${key}-i${idx++}`} className="italic">{token.slice(1, -1)}</em>)
    else if (token.startsWith('`'))
      parts.push(<code key={`${key}-c${idx++}`}
        className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono text-slate-700">
        {token.slice(1, -1)}
      </code>)
    lastIndex = match.index + token.length
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex))
  return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : parts
}

function MarkdownContent({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  const elements = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed.startsWith('### ')) {
      elements.push(<p key={i} className="text-[11px] font-bold uppercase tracking-wide text-slate-400 mt-3 mb-1">{renderInline(trimmed.slice(4), `h3-${i}`)}</p>)
      i++; continue
    }
    if (trimmed.startsWith('## ')) {
      elements.push(<p key={i} className="text-sm font-bold text-slate-800 mt-3 mb-1">{renderInline(trimmed.slice(3), `h2-${i}`)}</p>)
      i++; continue
    }
    if (trimmed.startsWith('# ')) {
      elements.push(<p key={i} className="text-base font-bold text-slate-800 mt-2 mb-1">{renderInline(trimmed.slice(2), `h1-${i}`)}</p>)
      i++; continue
    }
    if (trimmed === '---') {
      elements.push(<hr key={i} className="my-2 border-slate-100" />)
      i++; continue
    }
    if (trimmed.match(/^[-*•] /)) {
      const items = []
      while (i < lines.length && lines[i].trim().match(/^[-*•] /)) {
        const content = lines[i].trim().replace(/^[-*•] /, '')
        items.push(<li key={i} className="text-sm leading-relaxed text-slate-700">{renderInline(content, `li-${i}`)}</li>)
        i++
      }
      elements.push(<ul key={`ul-${i}`} className="list-disc list-outside pl-4 my-1.5 space-y-0.5">{items}</ul>)
      continue
    }
    if (trimmed.match(/^\d+[\.)]\s/)) {
      const items = []
      while (i < lines.length && lines[i].trim().match(/^\d+[\.)]\s/)) {
        const content = lines[i].trim().replace(/^\d+[\.)]\s/, '')
        items.push(<li key={i} className="text-sm leading-relaxed text-slate-700">{renderInline(content, `li-${i}`)}</li>)
        i++
      }
      elements.push(<ol key={`ol-${i}`} className="list-decimal list-outside pl-4 my-1.5 space-y-0.5">{items}</ol>)
      continue
    }
    if (trimmed === '') {
      if (elements.length > 0) elements.push(<div key={i} className="h-1.5" />)
      i++; continue
    }
    elements.push(<p key={i} className="text-sm leading-relaxed text-slate-700">{renderInline(trimmed, `p-${i}`)}</p>)
    i++
  }

  return <div className="space-y-0.5">{elements}</div>
}

// ── Copy button ──────────────────────────────────────────────────────────────
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch {}
  }
  return (
    <button onClick={copy} title="Copy"
      className="copy-btn opacity-0 group-hover:opacity-100 p-1.5 rounded-lg transition-all hover:bg-slate-100"
      style={{ color: copied ? '#10b981' : '#94a3b8' }}>
      {copied ? (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  )
}

// ── Source file badge ─────────────────────────────────────────────────────────
function FileBadge({ filename }) {
  const ext = (filename || '').split('.').pop().toLowerCase()
  const M = {
    pdf:  { bg: '#fee2e2', c: '#dc2626', t: 'PDF' },
    docx: { bg: '#dbeafe', c: '#2563eb', t: 'DOCX' },
    xlsx: { bg: '#dcfce7', c: '#16a34a', t: 'XLSX' },
    pptx: { bg: '#ffedd5', c: '#ea580c', t: 'PPTX' },
    png:  { bg: '#fef3c7', c: '#d97706', t: 'PNG' },
    jpg:  { bg: '#fef3c7', c: '#d97706', t: 'JPG' },
    txt:  { bg: '#f1f5f9', c: '#64748b', t: 'TXT' },
    md:   { bg: '#ede9fe', c: '#7c3aed', t: 'MD' },
  }
  const info = M[ext] || { bg: '#f1f5f9', c: '#64748b', t: ext?.toUpperCase() || 'DOC' }
  return (
    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
      style={{ backgroundColor: info.bg, color: info.c }}>
      {info.t}
    </span>
  )
}

// ── Main MessageBubble ───────────────────────────────────────────────────────
export default function MessageBubble({ message }) {
  const [showSources, setShowSources] = useState(false)
  const isUser      = message.role === 'user'
  const isError     = message.isError
  const isStreaming = message.streaming === true

  return (
    <div className={`flex gap-3 mb-5 message-enter group ${isUser ? 'flex-row-reverse' : ''}`}>

      {/* Avatar */}
      <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm"
        style={{
          background: isUser
            ? 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
            : isError ? '#fef2f2' : '#ffffff',
          border: isUser ? 'none' : isError ? '1px solid #fecaca' : '1px solid #e2e8f0',
        }}>
        {isUser ? (
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        ) : isError ? (
          <span className="text-xs font-bold text-red-500">!</span>
        ) : (
          <BotAvatar size="sm" />
        )}
      </div>

      {/* Content */}
      <div className={`max-w-[82%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>

        {/* Label */}
        <div className={`flex items-center gap-2 mb-1.5 ${isUser ? 'flex-row-reverse' : ''}`}>
          <p className="text-xs font-semibold text-slate-500">
            {isUser ? 'You' : 'KYC Assistant'}
          </p>
          {!isUser && !isError && !isStreaming && message.content && (
            <CopyButton text={message.content} />
          )}
        </div>

        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? 'rounded-tr-sm text-white'
            : isError
            ? 'bg-red-50 border border-red-100 rounded-tl-sm'
            : 'bg-white border border-slate-200 rounded-tl-sm'
        }`}
          style={isUser ? { background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' } : {}}>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : isError ? (
            <p className="text-sm text-red-600 leading-relaxed">{message.content}</p>
          ) : isStreaming ? (
            <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">
              {message.content}<span className="typing-cursor">▍</span>
            </p>
          ) : (
            <MarkdownContent text={message.content} />
          )}
        </div>

        {/* Sources */}
        {!isUser && !isError && !isStreaming && message.sources?.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-xs font-medium transition-colors px-2 py-1 rounded-lg hover:bg-slate-100"
              style={{ color: '#6366f1' }}>
              <svg className={`w-3 h-3 transition-transform duration-200 ${showSources ? 'rotate-90' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              {message.sources.length} source{message.sources.length > 1 ? 's' : ''} referenced
            </button>

            {showSources && (
              <div className="mt-1.5 space-y-1.5 source-enter">
                {message.sources.map((src, idx) => (
                  <div key={idx} className="bg-slate-50 border border-slate-100 rounded-xl p-2.5">
                    <div className="flex items-center gap-2 mb-1">
                      <FileBadge filename={src.metadata?.source || ''} />
                      <span className="text-xs font-medium text-slate-600 truncate">
                        {src.metadata?.source || 'Document'}
                        {src.metadata?.page && <span className="ml-1 text-slate-400">· p.{src.metadata.page}</span>}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">{src.content}</p>
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
