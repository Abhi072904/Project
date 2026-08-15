import { useState, useRef, useCallback } from 'react'

export default function UploadPanel({ onUpload }) {
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState('idle') // idle | uploading | done | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleFile = useCallback(
    async (file) => {
      if (!file) return
      if (!file.name.toLowerCase().endsWith('.csv')) {
        setStatus('error')
        setError('That file needs to be a .csv export from your bank or card statement.')
        return
      }
      setStatus('uploading')
      setError(null)
      try {
        const res = await onUpload(file)
        setResult(res)
        setStatus('done')
      } catch (err) {
        setStatus('error')
        setError(err.message || 'Upload failed.')
      }
    },
    [onUpload]
  )

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFile(e.dataTransfer.files?.[0])
      }}
      className={`border rounded-lg p-5 transition-colors ${
        dragging ? 'border-stamp bg-stamp/5' : 'border-dashed border-line bg-paper-raised'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="sr-only"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      {status === 'uploading' ? (
        <p className="font-mono text-sm text-ink-soft text-center py-2">Reconciling the ledger…</p>
      ) : status === 'done' && result ? (
        <div className="text-center py-1">
          <p className="font-body text-sm text-ink">
            <span className="font-semibold">{result.transactions_ingested}</span> new transactions ingested
            {result.duplicates_skipped > 0 && (
              <span className="text-ink-soft"> · {result.duplicates_skipped} duplicates skipped</span>
            )}
          </p>
          <button
            onClick={() => {
              setStatus('idle')
              setResult(null)
            }}
            className="font-mono text-xs uppercase tracking-wide text-stamp mt-2 hover:underline"
          >
            Upload another statement
          </button>
        </div>
      ) : (
        <div className="text-center">
          <p className="font-body text-sm text-ink-soft mb-2">
            Drop a bank or card CSV export here, or
          </p>
          <button
            onClick={() => inputRef.current?.click()}
            className="font-mono text-xs uppercase tracking-wide px-4 py-2 rounded bg-stamp text-paper hover:opacity-90 transition-opacity"
          >
            Choose a file
          </button>
          {status === 'error' && <p className="font-body text-xs text-leak mt-2">{error}</p>}
        </div>
      )}
    </div>
  )
}
