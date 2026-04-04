import React, { useState, useEffect, useRef } from 'react'

const FILE_COLORS = {
  pdf: '#ef4444', docx: '#2563eb', xlsx: '#16a34a',
  pptx: '#ea580c', txt: '#64748b', md: '#7c3aed',
  png: '#f59e0b', jpg: '#f59e0b', jpeg: '#f59e0b',
}

function fileColor(name) {
  const ext = name?.split('.').pop().toLowerCase() || ''
  return FILE_COLORS[ext] || '#94a3b8'
}

function FileIcon({ name }) {
  const ext = (name?.split('.').pop() || '').toUpperCase().slice(0, 4)
  return (
    <span
      className="text-white text-[8px] font-bold px-1 py-0.5 rounded flex-shrink-0"
      style={{ backgroundColor: fileColor(name) }}
    >
      {ext}
    </span>
  )
}

function MiniBar({ job }) {
  const pct =
    job.status === 'ready'    ? 100 :
    job.status === 'failed'   ? 100 :
    job.status === 'queued'   ? 3   :
    job.status === 'uploading'? 8   :
    typeof job.progress === 'number' ? Math.min(job.progress, 98) : 20

  const barColor =
    job.status === 'ready'  ? '#22c55e' :
    job.status === 'failed' ? '#ef4444' : '#3b82f6'

  return (
    <div className="h-1 rounded-full bg-white/20 overflow-hidden mt-1">
      <div
        className="h-full rounded-full"
        style={{
          width: `${pct}%`,
          backgroundColor: barColor,
          transition: 'width 0.6s ease-out',
        }}
      />
    </div>
  )
}

export default function ProcessingBadge({ jobs, onReopen }) {
  const [expanded, setExpanded]     = useState(true)
  const [dismissed, setDismissed]   = useState(false)
  const [fadeOut, setFadeOut]       = useState(false)
  const autoDismissRef              = useRef(null)

  const activeJobs    = jobs.filter(j => j.status === 'processing' || j.status === 'queued' || j.status === 'uploading')
  const completedJobs = jobs.filter(j => j.status === 'ready')
  const failedJobs    = jobs.filter(j => j.status === 'failed')
  const allDone       = jobs.length > 0 && activeJobs.length === 0

  // Auto-dismiss 4s after everything finishes
  useEffect(() => {
    if (allDone) {
      autoDismissRef.current = setTimeout(() => {
        setFadeOut(true)
        setTimeout(() => setDismissed(true), 400)
      }, 4000)
    }
    return () => clearTimeout(autoDismissRef.current)
  }, [allDone])

  // When a new batch starts (jobs reset), un-dismiss
  useEffect(() => {
    if (jobs.length > 0 && !allDone) {
      setDismissed(false)
      setFadeOut(false)
      clearTimeout(autoDismissRef.current)
    }
  }, [jobs.length])

  if (dismissed || jobs.length === 0) return null

  const processingCount = activeJobs.length
  const doneCount       = completedJobs.length + failedJobs.length

  return (
    <div
      className="fixed top-4 right-4 z-50 select-none"
      style={{
        transition: 'opacity 0.4s ease, transform 0.4s ease',
        opacity: fadeOut ? 0 : 1,
        transform: fadeOut ? 'translateY(-8px)' : 'translateY(0)',
        pointerEvents: fadeOut ? 'none' : 'auto',
      }}
    >
      {/* ── Main card ──────────────────────────────────────────── */}
      <div
        className="rounded-2xl shadow-2xl overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #1a2744 0%, #1e3a6e 100%)',
          minWidth: '260px',
          maxWidth: '320px',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        {/* Header row */}
        <div
          className="flex items-center gap-2 px-3 py-2.5 cursor-pointer"
          onClick={() => setExpanded(e => !e)}
        >
          {/* Pulsing dot */}
          <div className="relative flex-shrink-0">
            {!allDone ? (
              <>
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: '#3b82f6' }}
                />
                <div
                  className="absolute inset-0 w-2.5 h-2.5 rounded-full"
                  style={{
                    backgroundColor: '#3b82f6',
                    animation: 'badgePulse 1.4s ease-in-out infinite',
                  }}
                />
              </>
            ) : failedJobs.length > 0 && completedJobs.length === 0 ? (
              <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
            ) : (
              <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
            )}
          </div>

          {/* Label */}
          <span className="text-white text-xs font-semibold flex-1 leading-tight">
            {allDone
              ? failedJobs.length > 0 && completedJobs.length === 0
                ? `${failedJobs.length} file${failedJobs.length > 1 ? 's' : ''} failed`
                : `${doneCount} file${doneCount > 1 ? 's' : ''} ready ✓`
              : `Processing ${processingCount} file${processingCount > 1 ? 's' : ''}…`}
          </span>

          {/* Chevron */}
          <svg
            className="w-3.5 h-3.5 text-white/50 flex-shrink-0 transition-transform duration-200"
            style={{ transform: expanded ? 'rotate(0deg)' : 'rotate(180deg)' }}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
          </svg>

          {/* Dismiss X */}
          <button
            onClick={(e) => { e.stopPropagation(); setFadeOut(true); setTimeout(() => setDismissed(true), 400) }}
            className="ml-0.5 p-0.5 rounded hover:bg-white/10 transition-colors"
          >
            <svg className="w-3 h-3 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Overall progress strip (top of card) */}
        {!allDone && (
          <div className="h-0.5 bg-white/10">
            <div
              className="h-full bg-blue-400"
              style={{
                width: jobs.length
                  ? `${Math.round((doneCount / jobs.length) * 100)}%`
                  : '0%',
                transition: 'width 0.6s ease-out',
              }}
            />
          </div>
        )}

        {/* Expanded job list */}
        {expanded && (
          <div className="px-3 pb-3 pt-1 space-y-2 max-h-64 overflow-y-auto">
            {jobs.map((job, i) => {
              const statusLabel =
                job.status === 'ready'     ? 'Ready' :
                job.status === 'failed'    ? 'Failed' :
                job.status === 'queued'    ? 'Queued…' :
                job.status === 'uploading' ? 'Uploading…' :
                job.stage || 'Processing…'

              const pct =
                job.status === 'ready'    ? 100 :
                job.status === 'failed'   ? 100 :
                job.status === 'queued'   ? 3   :
                job.status === 'uploading'? 8   :
                typeof job.progress === 'number' ? Math.min(job.progress, 98) : 20

              return (
                <div key={i} className="rounded-xl p-2" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}>
                  {/* File name row */}
                  <div className="flex items-center gap-1.5">
                    <FileIcon name={job.name} />
                    <span className="text-white/90 text-[11px] font-medium truncate flex-1">{job.name}</span>
                    <span
                      className="text-[10px] font-bold flex-shrink-0"
                      style={{
                        color: job.status === 'ready'  ? '#4ade80' :
                               job.status === 'failed' ? '#f87171' : '#93c5fd',
                      }}
                    >
                      {job.status === 'ready'  ? `✓ ${job.chunks || 0}` :
                       job.status === 'failed' ? '✗' :
                       `${pct}%`}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <MiniBar job={job} />

                  {/* Stage label */}
                  <p
                    className="text-[10px] mt-1 truncate"
                    style={{
                      color: job.status === 'ready'  ? '#4ade80' :
                             job.status === 'failed' ? '#f87171' : 'rgba(255,255,255,0.45)',
                    }}
                  >
                    {job.status === 'ready'  ? `${job.chunks || 0} chunks indexed` :
                     job.status === 'failed' ? job.message || 'Failed' :
                     statusLabel}
                  </p>
                </div>
              )
            })}

            {/* Re-open modal link */}
            <button
              onClick={onReopen}
              className="w-full text-[10px] text-blue-300/70 hover:text-blue-200 transition-colors text-center pt-1"
            >
              Tap to open upload panel ↗
            </button>
          </div>
        )}
      </div>

      {/* Keyframes */}
      <style>{`
        @keyframes badgePulse {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50%       { opacity: 0; transform: scale(2.2); }
        }
      `}</style>
    </div>
  )
}
