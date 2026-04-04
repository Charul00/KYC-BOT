import React, { useState, useRef, useCallback, useEffect } from 'react'
import axios from 'axios'

const MAX_FILES = 10
const MAX_SIZE_MB = 20

const ALLOWED_EXT = ['.txt', '.pdf', '.docx', '.md', '.xlsx', '.png', '.jpg', '.jpeg', '.pptx']

const FILE_ICONS = {
  '.pdf':  { color: '#ef4444', label: 'PDF' },
  '.docx': { color: '#2563eb', label: 'WORD' },
  '.xlsx': { color: '#16a34a', label: 'XLS' },
  '.txt':  { color: '#64748b', label: 'TXT' },
  '.md':   { color: '#7c3aed', label: 'MD' },
  '.png':  { color: '#f59e0b', label: 'PNG' },
  '.jpg':  { color: '#f59e0b', label: 'JPG' },
  '.jpeg': { color: '#f59e0b', label: 'JPEG' },
  '.pptx': { color: '#ea580c', label: 'PPT' },
}

const JOB_STATUS_CONFIG = {
  queued:     { label: 'Queued',     barColor: '#94a3b8', bgColor: '#f8fafc', borderColor: '#e2e8f0', textColor: '#94a3b8' },
  processing: { label: 'Processing', barColor: '#3b82f6', bgColor: '#eff6ff', borderColor: '#bfdbfe', textColor: '#3b82f6' },
  ready:      { label: 'Done',       barColor: '#22c55e', bgColor: '#f0fdf4', borderColor: '#bbf7d0', textColor: '#16a34a' },
  failed:     { label: 'Failed',     barColor: '#ef4444', bgColor: '#fef2f2', borderColor: '#fecaca', textColor: '#dc2626' },
  uploading:  { label: 'Uploading',  barColor: '#3b82f6', bgColor: '#eff6ff', borderColor: '#bfdbfe', textColor: '#3b82f6' },
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
    if (sizeMB <= 2)  return '15–30 sec'
    if (sizeMB <= 8)  return '1–2 min'
    return '2–8 min (vision API per page)'
  }
  if (ext === '.docx') {
    if (sizeMB <= 2)  return '10–20 sec'
    if (sizeMB <= 8)  return '1–3 min'
    return '3–10 min (embedded images)'
  }
  if (ext === '.xlsx') {
    if (sizeMB <= 2)  return '10–20 sec'
    if (sizeMB <= 8)  return '20–60 sec'
    return '1–3 min (large dataset)'
  }
  if (ext === '.txt' || ext === '.md') return '5–15 sec'
  if (['.png', '.jpg', '.jpeg'].includes(ext)) return '20–60 sec (OCR + vision)'
  if (ext === '.pptx') {
    if (sizeMB <= 5)  return '30–60 sec'
    if (sizeMB <= 15) return '1–3 min'
    return '3–8 min'
  }
  return '15–90 sec'
}

// Dynamic poll timeout: 90 seconds per MB + 3 min base, min 10 min
function maxWaitMs(sizeMB) {
  return Math.max(10 * 60 * 1000, sizeMB * 90_000 + 3 * 60 * 1000)
}

async function pollJob(apiBase, jobId, sizeMB, onUpdate, signal) {
  const INTERVAL_MS = 2000
  const MAX_WAIT_MS = maxWaitMs(sizeMB || 1)
  const startTime = Date.now()

  while (Date.now() - startTime < MAX_WAIT_MS) {
    if (signal?.aborted) return
    await new Promise(r => setTimeout(r, INTERVAL_MS))
    if (signal?.aborted) return

    try {
      const res = await axios.get(`${apiBase}/documents/status/${jobId}`)
      const job = res.data
      onUpdate(job)
      if (job.status === 'ready' || job.status === 'failed') return
    } catch {
      // network hiccup — keep polling
    }
  }
  onUpdate({ status: 'failed', message: 'Processing timed out. Please try again.', chunks_created: 0 })
}

// Animated progress bar for a single job entry
// Uses REAL backend progress (job.progress 0-100) when available.
// Falls back to a smooth CSS transition between polled values.
function JobProgressBar({ item }) {
  // `item.progress` is the real backend percentage (0-100), may be undefined for old jobs
  // `displayPct` is what we actually render — we animate toward the target
  const [displayPct, setDisplayPct] = useState(0)
  const animRef = useRef(null)
  const prevTargetRef = useRef(0)

  // Target percentage based on status + real backend progress
  const targetPct = (() => {
    if (item.status === 'ready')    return 100
    if (item.status === 'failed')   return 100
    if (item.status === 'queued')   return 3
    if (item.status === 'uploading') return 8
    // processing: use real backend progress if available
    if (typeof item.progress === 'number' && item.progress > 0) {
      return Math.min(item.progress, 98)
    }
    return Math.max(displayPct, 10) // keep current if no backend signal yet
  })()

  useEffect(() => {
    if (animRef.current) cancelAnimationFrame(animRef.current)

    const from = displayPct
    const to   = targetPct
    if (from === to) return

    // Only animate forward — never step backwards
    if (to < from && item.status !== 'failed') return

    const duration = Math.abs(to - from) > 20 ? 600 : 350 // ms
    const startTime = performance.now()

    const step = (now) => {
      const ratio  = Math.min((now - startTime) / duration, 1)
      const eased  = 1 - Math.pow(1 - ratio, 3) // cubic ease-out
      const next   = from + (to - from) * eased
      setDisplayPct(Math.round(next))
      if (ratio < 1) animRef.current = requestAnimationFrame(step)
    }
    animRef.current = requestAnimationFrame(step)
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetPct, item.status])

  const cfg = JOB_STATUS_CONFIG[item.status] || JOB_STATUS_CONFIG.queued
  const pct = displayPct

  // Stage label from backend (e.g. "Page 47 of 274…")
  const stageLabel = item.stage || ''

  return (
    <div
      className="rounded-xl border p-3"
      style={{ backgroundColor: cfg.bgColor, borderColor: cfg.borderColor }}
    >
      {/* File name row */}
      <div className="flex items-center gap-2 mb-2">
        <FileTypeBadge ext={'.' + item.name.split('.').pop().toLowerCase()} />
        <span className="text-xs text-slate-700 truncate flex-1 font-medium">{item.name}</span>
        <span className="text-xs font-semibold flex-shrink-0" style={{ color: cfg.textColor }}>
          {item.status === 'ready'  ? `✓ ${item.chunks || 0} chunks` :
           item.status === 'failed' ? '✗ Failed' :
           `${pct}%`}
        </span>
      </div>

      {/* Progress bar — real progress + shimmer shimmer during processing */}
      <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
        {item.status === 'processing' ? (
          <div className="relative h-full">
            {/* Solid fill = real progress */}
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{
                width: `${pct}%`,
                backgroundColor: cfg.barColor,
                transition: 'width 0.5s ease-out',
              }}
            />
            {/* Moving shimmer on top */}
            <div
              style={{
                position: 'absolute',
                top: 0, bottom: 0,
                left: `${Math.max(0, pct - 20)}%`,
                width: '20%',
                background: `linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent)`,
                animation: 'shimmer 1.6s ease-in-out infinite',
              }}
            />
          </div>
        ) : (
          <div
            className="h-full rounded-full"
            style={{
              width: `${pct}%`,
              backgroundColor: cfg.barColor,
              transition: 'width 0.6s ease-out',
            }}
          />
        )}
      </div>

      {/* Stage + message row */}
      <div className="flex items-center justify-between mt-1.5">
        <p className="text-[11px]" style={{ color: cfg.textColor }}>
          {item.status === 'ready'    ? item.message || 'Ready to query' :
           item.status === 'failed'   ? item.message || 'Processing failed' :
           item.status === 'queued'   ? 'Waiting in queue…' :
           item.status === 'uploading'? 'Uploading to server…' :
           stageLabel || item.message || 'Processing document…'}
        </p>
        {item.status === 'processing' && item.sizeMB > 5 && (
          <p className="text-[10px] text-slate-400 flex-shrink-0 ml-2">
            Est: {estimateProcessingTime({ name: item.name, size: item.sizeMB * 1024 * 1024 })}
          </p>
        )}
      </div>
    </div>
  )
}

export default function DocumentUpload({ onClose, apiBase, visible = true, onJobsChange }) {
  const [activeTab, setActiveTab]   = useState('upload')  // 'upload' | 'docs'
  const [files, setFiles]           = useState([])
  const [uploading, setUploading]   = useState(false)
  const [progress, setProgress]     = useState([])
  const [error, setError]           = useState(null)
  const [dragOver, setDragOver]     = useState(false)
  const [done, setDone]             = useState(false)
  const fileInputRef                = useRef(null)
  const abortRef                    = useRef(null)

  // ── My Documents state ──────────────────────────────────────────────────────
  const [docList, setDocList]         = useState([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)   // filename pending confirm
  const [deleting, setDeleting]         = useState(false)
  const [deleteResult, setDeleteResult] = useState(null)   // {ok, message}

  // Notify parent whenever job progress changes — powers the floating badge
  useEffect(() => {
    onJobsChange?.(progress)
  }, [progress, onJobsChange])

  // When modal becomes visible again, reset if previous batch fully finished
  useEffect(() => {
    if (visible && done && progress.every(p => p.status === 'ready' || p.status === 'failed')) {
      // Only auto-reset if user re-opens after full completion
    }
  }, [visible])

  // Fetch document list when switching to the docs tab
  const fetchDocs = useCallback(async () => {
    setDocsLoading(true)
    try {
      const res = await axios.get(`${apiBase}/documents`)
      setDocList(res.data.documents || [])
    } catch {
      setDocList([])
    } finally {
      setDocsLoading(false)
    }
  }, [apiBase])

  useEffect(() => {
    if (activeTab === 'docs' && visible) fetchDocs()
  }, [activeTab, visible, fetchDocs])

  // Confirm delete
  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      const res = await axios.delete(`${apiBase}/documents/${encodeURIComponent(deleteTarget)}`)
      setDeleteResult({ ok: true, message: res.data.message })
      setDocList(prev => prev.filter(d => d.filename !== deleteTarget))
    } catch (err) {
      const msg = err.response?.data?.detail || 'Delete failed. Please try again.'
      setDeleteResult({ ok: false, message: msg })
    } finally {
      setDeleting(false)
      setDeleteTarget(null)
    }
  }

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
        setError(`"${f.name}" exceeds ${MAX_SIZE_MB} MB limit.`)
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

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); validateAndAdd(Array.from(e.dataTransfer.files)) }
  const handleFileSelect = (e) => { validateAndAdd(Array.from(e.target.files)); e.target.value = '' }
  const removeFile = (name) => setFiles(prev => prev.filter(f => f.name !== name))

  const updateProgress = useCallback((index, patch) => {
    setProgress(prev => prev.map((p, i) => i === index ? { ...p, ...patch } : p))
  }, [])

  const handleUpload = async () => {
    if (!files.length) return

    setUploading(true)
    setError(null)
    setDone(false)

    const initial = files.map(f => ({
      name: f.name,
      sizeMB: f.size / (1024 * 1024),
      status: 'uploading',
      message: `Estimated: ${estimateProcessingTime(f)}`,
      chunks: 0,
      jobId: null,
    }))
    setProgress(initial)

    const controller = new AbortController()
    abortRef.current = controller

    const formData = new FormData()
    files.forEach(f => formData.append('files', f))

    let jobMap = {}

    try {
      const res = await axios.post(`${apiBase}/documents/upload-async`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
        signal: controller.signal,
      })

      const { jobs = [], errors = [] } = res.data

      jobs.forEach(job => {
        const idx = initial.findIndex(p => p.name === job.filename)
        if (idx !== -1) {
          jobMap[job.filename] = { jobId: job.job_id, index: idx }
          updateProgress(idx, { status: 'queued', message: 'Queued for processing…', jobId: job.job_id })
        }
      })

      errors.forEach(err => {
        const idx = initial.findIndex(p => p.name === err.filename)
        if (idx !== -1) updateProgress(idx, { status: 'failed', message: err.message })
      })

    } catch (err) {
      const isTimeout = err.code === 'ECONNABORTED'
      const msg = err.response?.data?.detail || (isTimeout ? 'Upload timed out. Try splitting files.' : 'Upload failed. Please retry.')
      setProgress(prev => prev.map(p => ({ ...p, status: 'failed', message: msg })))
      setUploading(false)
      setDone(true)
      setFiles([])
      return
    }

    const pollPromises = Object.values(jobMap).map(({ jobId, index }) => {
      const sizeMB = initial[index]?.sizeMB || 1
      return pollJob(
        apiBase,
        jobId,
        sizeMB,
        (job) => {
          // Map all backend fields through so JobProgressBar gets real progress + stage
          const msg = job.status === 'ready'
            ? `${job.chunks_created || 0} chunks indexed`
            : job.status === 'failed'
            ? (job.message || 'Processing failed')
            : job.message || 'Processing document…'
          updateProgress(index, {
            status:   job.status,
            message:  msg,
            chunks:   job.chunks_created || 0,
            progress: job.progress,        // real backend 0-100
            stage:    job.stage || '',     // e.g. "Page 47 of 274…"
          })
        },
        controller.signal,
      )
    })

    await Promise.allSettled(pollPromises)
    setUploading(false)
    setDone(true)
    setFiles([])
  }

  const handleCancel = () => {
    abortRef.current?.abort()
    setUploading(false)
    setDone(true)
  }

  const successCount = progress.filter(p => p.status === 'ready').length
  const errorCount   = progress.filter(p => p.status === 'failed').length

  // When hidden: render nothing but stay mounted so polling continues in background
  if (!visible) return null

  return (
    <>
      {/* CSS for shimmer animation */}
      <style>{`
        @keyframes shimmer {
          0%   { opacity: 0; transform: translateX(-150%); }
          40%  { opacity: 1; }
          60%  { opacity: 1; }
          100% { opacity: 0; transform: translateX(600%); }
        }
      `}</style>

      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <div
          className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold" style={{ color: '#1a2744' }}>Documents</h2>
            <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-lg">
              <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-4 p-1 bg-slate-100 rounded-xl">
            {[
              { id: 'upload', label: 'Upload' },
              { id: 'docs',   label: 'My Documents' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); setDeleteResult(null) }}
                className="flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all"
                style={activeTab === tab.id
                  ? { backgroundColor: '#fff', color: '#1a2744', boxShadow: '0 1px 4px rgba(0,0,0,0.10)' }
                  : { color: '#94a3b8', backgroundColor: 'transparent' }}
              >
                {tab.label}
                {tab.id === 'docs' && docList.length > 0 && (
                  <span
                    className="ml-1 px-1.5 py-0.5 rounded-full text-[9px]"
                    style={{ backgroundColor: '#e2e8f0', color: '#64748b' }}
                  >
                    {docList.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* ── MY DOCUMENTS TAB ─────────────────────────────────────────────── */}
          {activeTab === 'docs' && (
            <div>
              {/* Delete result flash */}
              {deleteResult && (
                <div
                  className="mb-3 px-3 py-2 rounded-lg text-xs font-medium"
                  style={{
                    backgroundColor: deleteResult.ok ? '#f0fdf4' : '#fef2f2',
                    color: deleteResult.ok ? '#16a34a' : '#dc2626',
                    border: `1px solid ${deleteResult.ok ? '#bbf7d0' : '#fecaca'}`,
                  }}
                >
                  {deleteResult.ok ? '✓ ' : '✗ '}{deleteResult.message}
                  <button className="float-right opacity-50 hover:opacity-100" onClick={() => setDeleteResult(null)}>×</button>
                </div>
              )}

              {docsLoading ? (
                <div className="py-10 text-center text-slate-400 text-sm">Loading…</div>
              ) : docList.length === 0 ? (
                <div className="py-10 text-center">
                  <svg className="w-10 h-10 text-slate-200 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                  </svg>
                  <p className="text-sm text-slate-400">No documents uploaded yet.</p>
                  <button
                    onClick={() => setActiveTab('upload')}
                    className="mt-2 text-xs text-blue-500 hover:underline"
                  >
                    Upload your first document →
                  </button>
                </div>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {docList.map((doc) => {
                    const ext = doc.filename.split('.').pop().toLowerCase()
                    const color = FILE_ICONS[`.${ext}`]?.color || '#94a3b8'
                    const label = FILE_ICONS[`.${ext}`]?.label || ext.toUpperCase()
                    return (
                      <div
                        key={doc.filename}
                        className="rounded-xl border border-slate-100 bg-slate-50 p-3"
                      >
                        <div className="flex items-start gap-2">
                          {/* Badge */}
                          <span
                            className="text-white text-[9px] font-bold px-1.5 py-0.5 rounded mt-0.5 flex-shrink-0"
                            style={{ backgroundColor: color }}
                          >
                            {label}
                          </span>
                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-slate-700 truncate">{doc.filename}</p>
                            <p className="text-[10px] text-slate-400 mt-0.5">
                              {doc.size_mb} MB
                              {doc.uploaded_at && ` · ${new Date(doc.uploaded_at).toLocaleDateString()}`}
                            </p>
                          </div>
                          {/* Delete button */}
                          <button
                            onClick={() => { setDeleteTarget(doc.filename); setDeleteResult(null) }}
                            className="flex-shrink-0 p-1.5 rounded-lg hover:bg-red-50 text-slate-300 hover:text-red-400 transition-colors"
                            title="Delete document"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* ── DELETE CONFIRMATION ──────────────────────────────────────── */}
              {deleteTarget && (
                <div
                  className="mt-3 rounded-xl border-2 p-4"
                  style={{ borderColor: '#fecaca', backgroundColor: '#fff5f5' }}
                >
                  {/* Warning icon + title */}
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: '#fee2e2' }}
                    >
                      <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-red-700">Delete this document?</span>
                  </div>

                  {/* Filename */}
                  <p className="text-xs text-slate-600 mb-2 font-medium break-all">
                    "{deleteTarget}"
                  </p>

                  {/* Warning note */}
                  <div
                    className="rounded-lg p-2.5 mb-3 text-[11px] leading-relaxed"
                    style={{ backgroundColor: '#fef2f2', color: '#991b1b' }}
                  >
                    <span className="font-bold">⚠ Note: </span>
                    If you delete this file, all its indexed content will be permanently removed from the knowledge base.
                    The bot will <span className="font-bold">no longer be able to answer</span> any questions, perform
                    lookups, or run any operations based on this document. This action cannot be undone.
                  </div>

                  {/* Buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => setDeleteTarget(null)}
                      disabled={deleting}
                      className="flex-1 py-2 border border-slate-200 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-50 transition-colors disabled:opacity-40"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={confirmDelete}
                      disabled={deleting}
                      className="flex-1 py-2 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                      style={{ backgroundColor: '#dc2626' }}
                    >
                      {deleting ? 'Deleting…' : 'Yes, Delete'}
                    </button>
                  </div>
                </div>
              )}

              {/* Refresh link */}
              {!deleteTarget && (
                <button
                  onClick={fetchDocs}
                  className="mt-3 w-full text-[11px] text-slate-400 hover:text-slate-600 text-center transition-colors"
                >
                  ↻ Refresh list
                </button>
              )}
            </div>
          )}

          {/* ── UPLOAD TAB ────────────────────────────────────────────────── */}
          {activeTab === 'upload' && <>

          {/* Drop zone */}
          {!uploading && !done && (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                dragOver ? 'border-blue-400 bg-blue-50 scale-[1.01]' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                accept=".txt,.pdf,.docx,.md,.xlsx,.png,.jpg,.jpeg,.pptx"
                multiple
                className="hidden"
              />
              <svg className="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
              </svg>
              <p className="text-sm text-slate-500">
                Drop files here or <span className="text-blue-500 font-medium">browse</span>
              </p>
              <div className="flex flex-wrap justify-center gap-1.5 mt-2">
                {ALLOWED_EXT.map(ext => <FileTypeBadge key={ext} ext={ext} />)}
              </div>
            </div>
          )}

          {/* Selected files list */}
          {files.length > 0 && !uploading && !done && (
            <div className="mt-3 space-y-1.5 max-h-44 overflow-y-auto">
              {files.map(f => {
                const ext = '.' + f.name.split('.').pop().toLowerCase()
                return (
                  <div key={f.name} className="p-2 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileTypeBadge ext={ext} />
                        <span className="text-xs text-slate-600 truncate">{f.name}</span>
                        <span className="text-xs text-slate-400 flex-shrink-0">
                          {(f.size / (1024 * 1024)).toFixed(1)} MB
                        </span>
                      </div>
                      <button onClick={() => removeFile(f.name)} className="p-1 hover:bg-slate-200 rounded flex-shrink-0 ml-1">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">Est: {estimateProcessingTime(f)}</p>
                  </div>
                )
              })}
            </div>
          )}

          {/* Progress bars */}
          {progress.length > 0 && (
            <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
              {done && (
                <p className="text-xs font-semibold mb-1" style={{ color: '#1a2744' }}>
                  {successCount > 0 || errorCount > 0
                    ? `${successCount > 0 ? `✓ ${successCount} ready` : ''}${errorCount > 0 ? `  ✗ ${errorCount} failed` : ''}`
                    : 'Processing…'}
                </p>
              )}
              {uploading && (
                <p className="text-xs font-medium text-blue-500 mb-1">
                  Uploading &amp; processing in background…
                </p>
              )}
              {progress.map((p, i) => (
                <JobProgressBar key={i} item={p} />
              ))}
            </div>
          )}

          {/* Validation error */}
          {error && (
            <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs text-amber-700">{error}</p>
            </div>
          )}

          {/* Action buttons */}
          {!done ? (
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleUpload}
                disabled={files.length === 0 || uploading}
                className="flex-1 py-2.5 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed font-medium text-sm transition-colors"
                style={{ backgroundColor: '#2563eb' }}
              >
                {uploading ? 'Processing…' : `Upload ${files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : ''}`}
              </button>
              {uploading && (
                <button
                  onClick={handleCancel}
                  className="px-4 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
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
              <p className="text-xs text-slate-400 text-center leading-relaxed">
                ✓ PDF · ✓ Word · ✓ Excel · ✓ PowerPoint · ✓ Images · ✓ TXT
                <br/>
                <span className="text-slate-300">Up to {MAX_SIZE_MB} MB · Processed asynchronously</span>
              </p>
            </div>
          )}

          </> /* end UPLOAD TAB */}
        </div>
      </div>
    </>
  )
}
