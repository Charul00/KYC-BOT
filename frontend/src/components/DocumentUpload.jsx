import React, { useState, useRef } from 'react'
import axios from 'axios'

const MAX_FILES = 10
const MAX_SIZE_MB = 10
const ALLOWED_EXT = ['.txt', '.pdf', '.docx', '.md', '.xlsx']

const FILE_ICONS = {
  '.pdf':  { color: '#ef4444', label: 'PDF' },
  '.docx': { color: '#2563eb', label: 'WORD' },
  '.xlsx': { color: '#16a34a', label: 'XLS' },
  '.txt':  { color: '#64748b', label: 'TXT' },
  '.md':   { color: '#7c3aed', label: 'MD' },
}

function FileTypeBadge({ ext }) {
  const info = FILE_ICONS[ext] || { color: '#94a3b8', label: ext.replace('.', '').toUpperCase() }
  return (
    <span
      className="text-white text-[9px] font-bold px-1 py-0.5 rounded"
      style={{ backgroundColor: info.color }}
    >
      {info.label}
    </span>
  )
}

function estimateProcessingTime(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  const sizeMB = file.size / (1024 * 1024)

  if (ext === '.pdf') {
    if (sizeMB <= 0.3) return '10–20 sec'
    if (sizeMB <= 0.7) return '20–35 sec'
    return '35–60 sec'
  }

  if (ext === '.docx') {
    if (sizeMB <= 0.3) return '8–15 sec'
    if (sizeMB <= 0.7) return '15–25 sec'
    return '25–45 sec'
  }

  if (ext === '.xlsx') {
    if (sizeMB <= 0.3) return '12–25 sec'
    if (sizeMB <= 0.7) return '25–40 sec'
    return '40–60 sec'
  }

  if (ext === '.txt' || ext === '.md') {
    if (sizeMB <= 0.3) return '5–10 sec'
    if (sizeMB <= 0.7) return '10–20 sec'
    return '20–30 sec'
  }

  return '10–30 sec'
}

export default function DocumentUpload({ onClose, apiBase }) {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState([])
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [done, setDone] = useState(false)
  const fileInputRef = useRef(null)

  const validateAndAdd = (newFiles) => {
    setError(null)
    const valid = []

    for (const f of newFiles) {
      const ext = '.' + f.name.split('.').pop().toLowerCase()

      if (!ALLOWED_EXT.includes(ext)) {
        setError(`"${f.name}" — unsupported type. Allowed: ${ALLOWED_EXT.join(', ')}`)
        continue
      }

      if (f.size > MAX_SIZE_MB * 1024 * 1024) {
        setError(`"${f.name}" exceeds ${MAX_SIZE_MB}MB limit. Please upload a smaller file.`)
        continue
      }

      if (files.find(x => x.name === f.name)) continue
      valid.push(f)
    }

    setFiles(prev => {
      const next = [...prev, ...valid]
      if (next.length > MAX_FILES) {
        setError(`Maximum ${MAX_FILES} files at a time.`)
        return next.slice(0, MAX_FILES)
      }
      return next
    })
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    validateAndAdd(Array.from(e.dataTransfer.files))
  }

  const handleFileSelect = (e) => {
    validateAndAdd(Array.from(e.target.files))
    e.target.value = ''
  }

  const removeFile = (name) => {
    setFiles(prev => prev.filter(f => f.name !== name))
  }

  const handleUpload = async () => {
    if (!files.length) return

    setUploading(true)
    setError(null)
    setDone(false)

    const initial = files.map(f => ({
      name: f.name,
      status: 'pending',
      message: '',
      estimate: estimateProcessingTime(f),
    }))
    setProgress(initial)

    for (let i = 0; i < files.length; i++) {
      setProgress(prev =>
        prev.map((p, idx) =>
          idx === i
            ? { ...p, status: 'uploading', message: `Estimated time: ${p.estimate}` }
            : p
        )
      )

      const formData = new FormData()
      formData.append('files', files[i])

      try {
        const res = await axios.post(`${apiBase}/documents/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
        })

        const processed = res.data.processed?.[0]
        const failed = res.data.errors?.[0]

        if (processed) {
          setProgress(prev =>
            prev.map((p, idx) =>
              idx === i
                ? {
                    ...p,
                    status: 'success',
                    message: `${processed.chunks_created || 0} chunks indexed`,
                  }
                : p
            )
          )
        } else if (failed) {
          setProgress(prev =>
            prev.map((p, idx) =>
              idx === i
                ? { ...p, status: 'error', message: failed.message }
                : p
            )
          )
        }
      } catch (err) {
        const isTimeout =
          err.code === 'ECONNABORTED' ||
          err.name === 'TimeoutError' ||
          err.name === 'AbortError'

        const msg =
          err.response?.data?.detail ||
          (isTimeout
            ? 'Timed out — try a smaller file or upload only one file'
            : 'Upload failed')

        setProgress(prev =>
          prev.map((p, idx) =>
            idx === i
              ? { ...p, status: 'error', message: msg }
              : p
          )
        )
      }
    }

    setUploading(false)
    setDone(true)
    setFiles([])
  }

  const statusIcon = (status) => {
    if (status === 'uploading') {
      return (
        <svg className="w-3.5 h-3.5 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      )
    }
    if (status === 'success') return <span className="text-green-500 text-sm">✓</span>
    if (status === 'error') return <span className="text-red-500 text-sm">✗</span>
    return <span className="w-3.5 h-3.5 rounded-full border border-slate-300 inline-block" />
  }

  const successCount = progress.filter(p => p.status === 'success').length
  const errorCount = progress.filter(p => p.status === 'error').length

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>

        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-semibold" style={{ color: '#1a2744' }}>Upload Documents</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Max {MAX_FILES} files · {MAX_SIZE_MB}MB each · Upload one file at a time (recommended) · PDF, DOCX, XLSX, TXT, MD
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-lg">
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {!uploading && !done && (
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileSelect}
              accept=".txt,.pdf,.docx,.md,.xlsx"
              multiple
              className="hidden"
            />
            <svg className="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            <p className="text-sm text-slate-500">
              Drop files here or <span className="text-blue-500">browse</span>
            </p>
            <div className="flex flex-wrap justify-center gap-1.5 mt-2">
              {ALLOWED_EXT.map(ext => <FileTypeBadge key={ext} ext={ext} />)}
            </div>
          </div>
        )}

        {files.length > 0 && !uploading && !done && (
          <div className="mt-3 space-y-1.5 max-h-44 overflow-y-auto">
            {files.map(f => {
              const ext = '.' + f.name.split('.').pop().toLowerCase()
              return (
                <div key={f.name} className="p-2 bg-slate-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileTypeBadge ext={ext} />
                      <span className="text-xs text-slate-600 truncate">{f.name}</span>
                      <span className="text-xs text-slate-400 flex-shrink-0">
                        {(f.size / 1024).toFixed(0)} KB
                      </span>
                    </div>
                    <button onClick={() => removeFile(f.name)} className="p-1 hover:bg-slate-200 rounded flex-shrink-0 ml-1">
                      <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Estimated processing time: {estimateProcessingTime(f)}
                  </p>
                </div>
              )
            })}
          </div>
        )}

        {progress.length > 0 && (
          <div className="mt-3 space-y-1.5 max-h-52 overflow-y-auto">
            <p className="text-xs font-medium text-slate-500 mb-1">
              {uploading ? 'Processing files one by one…' : `Done — ${successCount} succeeded${errorCount ? `, ${errorCount} failed` : ''}`}
            </p>
            {progress.map((p, i) => (
              <div
                key={i}
                className={`flex items-center gap-2 p-2 rounded-lg text-xs border ${
                  p.status === 'success' ? 'bg-green-50 border-green-100' :
                  p.status === 'error' ? 'bg-red-50 border-red-100' :
                  p.status === 'uploading' ? 'bg-blue-50 border-blue-100' :
                  'bg-slate-50 border-slate-100'
                }`}
              >
                <span className="flex-shrink-0">{statusIcon(p.status)}</span>
                <span className="truncate text-slate-700 flex-1">{p.name}</span>
                {p.message && <span className="text-slate-400 flex-shrink-0">{p.message}</span>}
                {p.status === 'pending' && <span className="text-slate-400 flex-shrink-0">waiting…</span>}
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs text-amber-700">{error}</p>
          </div>
        )}

        {!done ? (
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || uploading}
            className="mt-4 w-full py-2.5 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed font-medium text-sm transition-colors"
            style={{ backgroundColor: '#2563eb' }}
          >
            {uploading
              ? `Uploading ${progress.filter(p => p.status === 'uploading').map(p => p.name)[0] || ''}…`
              : `Upload ${files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : ''}`
            }
          </button>
        ) : (
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => { setProgress([]); setDone(false); setError(null) }}
              className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Upload More
            </button>
            <button
              onClick={onClose}
              className="flex-1 py-2.5 text-white rounded-xl text-sm font-medium transition-colors"
              style={{ backgroundColor: '#2563eb' }}
            >
              Done
            </button>
          </div>
        )}

        {!uploading && !done && (
          <div className="mt-3 pt-3 border-t border-slate-100">
            <p className="text-xs text-slate-400 text-center">
              ✓ PDF · ✓ Word (DOCX) · ✓ Excel (XLSX) · ✓ TXT · ✓ Markdown
              &nbsp;&nbsp;|&nbsp;&nbsp;
              ⚠ Recommended: max 1MB per file · Upload files one by one for best performance
              &nbsp;&nbsp;|&nbsp;&nbsp;
              ⏱ Large or text-heavy files may take longer to process
              &nbsp;&nbsp;|&nbsp;&nbsp;
              ✗ Images · ✗ MP3 · ✗ ZIP
            </p>
          </div>
        )}

      </div>
    </div>
  )
}
