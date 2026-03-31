import React, { useState, useRef } from 'react'
import axios from 'axios'

export default function DocumentUpload({ onClose, apiBase }) {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)

  const allowedExtensions = ['.txt', '.pdf', '.docx', '.md']

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = Array.from(e.dataTransfer.files)
    validateAndAdd(dropped)
  }

  const handleFileSelect = (e) => {
    const selected = Array.from(e.target.files)
    validateAndAdd(selected)
    e.target.value = '' // reset so same file can be re-selected
  }

  const validateAndAdd = (newFiles) => {
    setError(null)
    const valid = []
    for (const f of newFiles) {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      if (!allowedExtensions.includes(ext)) {
        setError(`"${f.name}" is not supported. Allowed: ${allowedExtensions.join(', ')}`)
        continue
      }
      if (f.size > 10 * 1024 * 1024) {
        setError(`"${f.name}" exceeds 10MB limit.`)
        continue
      }
      // Avoid duplicates
      if (!files.find(existing => existing.name === f.name)) {
        valid.push(f)
      }
    }
    setFiles(prev => [...prev, ...valid])
  }

  const removeFile = (name) => {
    setFiles(prev => prev.filter(f => f.name !== name))
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    setError(null)
    setResults(null)

    const formData = new FormData()
    files.forEach(f => formData.append('files', f))

    try {
      const res = await axios.post(`${apiBase}/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResults(res.data)
      setFiles([])
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const totalProcessed = results?.total_processed || 0
  const totalErrors = results?.total_errors || 0

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-semibold" style={{ color: '#1a2744' }}>Upload Documents</h2>
            <p className="text-xs text-slate-400 mt-0.5">Add KYC documents for the assistant to reference</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-lg">
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Drop Zone */}
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
            accept=".txt,.pdf,.docx,.md"
            multiple
            className="hidden"
          />
          <svg className="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-slate-500">Drop files here or click to browse</p>
          <p className="text-xs text-slate-400 mt-1">TXT, PDF, DOCX, MD &middot; Max 10MB each</p>
        </div>

        {/* Selected Files List */}
        {files.length > 0 && (
          <div className="mt-3 space-y-1.5 max-h-32 overflow-y-auto">
            {files.map(f => (
              <div key={f.name} className="flex items-center justify-between p-2 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-2 min-w-0">
                  <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-xs text-slate-600 truncate">{f.name}</span>
                  <span className="text-xs text-slate-400 flex-shrink-0">{(f.size / 1024).toFixed(0)} KB</span>
                </div>
                <button onClick={() => removeFile(f.name)} className="p-1 hover:bg-slate-200 rounded flex-shrink-0">
                  <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-3 p-2.5 bg-red-50 border border-red-100 rounded-lg">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="mt-3 p-2.5 bg-green-50 border border-green-100 rounded-lg">
            <p className="text-xs text-green-700 font-medium">
              {totalProcessed} document{totalProcessed !== 1 ? 's' : ''} processed successfully
              {totalErrors > 0 && ` (${totalErrors} failed)`}
            </p>
            {results.processed?.map((r, i) => (
              <p key={i} className="text-xs text-green-600 mt-0.5">&#10003; {r.filename}</p>
            ))}
            {results.errors?.map((r, i) => (
              <p key={i} className="text-xs text-red-500 mt-0.5">&#10007; {r.filename}: {r.message}</p>
            ))}
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          className="mt-4 w-full py-2.5 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed font-medium text-sm transition-colors"
          style={{ backgroundColor: '#2563eb' }}
        >
          {uploading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              Processing Documents...
            </span>
          ) : (
            `Upload ${files.length > 0 ? `(${files.length} file${files.length > 1 ? 's' : ''})` : ''}`
          )}
        </button>
      </div>
    </div>
  )
}
