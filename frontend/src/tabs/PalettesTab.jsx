import { useState, useEffect, useRef } from 'react'
import './PalettesTab.css'
import { PaletteStrip } from '../components/PaletteStrip'
import { RefreshCw, Upload, Trash2, Download } from 'lucide-react'

const API = '/api'

const SOURCE_LABELS = {
  default: 'defaults',
  user:    'my palettes',
  legacy:  'other',
}

const SOURCE_ORDER = ['default', 'user', 'legacy']

function PaletteRow({ palette, onDelete, onDownload }) {
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleDelete = () => {
    if (!confirmDelete) { setConfirmDelete(true); return }
    onDelete(palette.name)
    setConfirmDelete(false)
  }

  return (
    <div className={`pal-row ${confirmDelete ? 'pal-row--confirm' : ''}`}>
      <div className="pal-row-info">
        <span className="pal-row-name">{palette.name.replace('.pal', '')}</span>
        <span className="pal-row-count">{palette.count} colors</span>
      </div>
      <div className="pal-row-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
      <div className="pal-row-actions">
        <button
          className="pal-icon-btn"
          title="download .pal"
          onClick={() => onDownload(palette.name)}
        >
          <Download size={12} />
        </button>
        {!palette.is_default && (
          <button
            className={`pal-icon-btn pal-icon-btn--danger ${confirmDelete ? 'confirming' : ''}`}
            title={confirmDelete ? 'click again to confirm' : 'delete palette'}
            onClick={handleDelete}
            onBlur={() => setConfirmDelete(false)}
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
    </div>
  )
}

export function PalettesTab() {
  const [palettes, setPalettes] = useState([])
  const [loading, setLoading] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  const fetchPalettes = async () => {
    setLoading(true)
    try {
      const data = await fetch(`${API}/palettes`).then(r => r.json())
      setPalettes(data)
    } catch {
      setError('Failed to load palettes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPalettes() }, [])

  const handleReload = async () => {
    setReloading(true)
    await fetch(`${API}/palettes/reload`, { method: 'POST' })
    await fetchPalettes()
    setReloading(false)
  }

  const handleUpload = async (files) => {
    setError(null)
    await Promise.all(Array.from(files).map(async (f) => {
      const fd = new FormData()
      fd.append('file', f)
      const res = await fetch(`${API}/palettes/upload`, { method: 'POST', body: fd })
      if (!res.ok) setError(`Failed to upload ${f.name}`)
    }))
    await fetchPalettes()
  }

  const handleDelete = async (name) => {
    const res = await fetch(`${API}/palettes/${encodeURIComponent(name)}`, { method: 'DELETE' })
    if (!res.ok) {
      const msg = await res.text()
      setError(msg)
      return
    }
    await fetchPalettes()
  }

  const handleDownload = (name) => {
    const a = document.createElement('a')
    a.href = `${API}/palettes/${encodeURIComponent(name)}/download`
    a.download = name
    a.click()
  }

  // Group palettes by source
  const grouped = SOURCE_ORDER.reduce((acc, src) => {
    acc[src] = palettes.filter(p => p.source === src)
    return acc
  }, {})

  const total = palettes.length
  const userCount = grouped.user?.length ?? 0

  return (
    <div className="tab-content">
      <div className="palettes-layout">

        {/* ── Left: controls ── */}
        <div className="palettes-left">
          <div className="palettes-stats">
            <span className="palettes-stat-num">{total}</span>
            <span className="palettes-stat-label">palettes loaded</span>
          </div>

          <div className="palettes-stat-row">
            <div className="palettes-stat-item">
              <span className="palettes-stat-num">{grouped.default?.length ?? 0}</span>
              <span className="palettes-stat-label">defaults</span>
            </div>
            <div className="palettes-stat-item">
              <span className="palettes-stat-num">{userCount}</span>
              <span className="palettes-stat-label">user</span>
            </div>
          </div>

          <div className="palettes-left-actions">
            <button
              className="btn-secondary"
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={12} /> upload .pal
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".pal"
              multiple
              style={{ display: 'none' }}
              onChange={e => { handleUpload(e.target.files); e.target.value = '' }}
            />

            <button
              className="btn-secondary"
              onClick={handleReload}
              disabled={reloading}
            >
              <RefreshCw size={12} className={reloading ? 'spinning' : ''} />
              reload
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}

          <div className="palettes-left-hint">
            <p>Put <code>.pal</code> files in <code>palettes/user/</code> or upload above.</p>
            <p>Files in <code>palettes/defaults/</code> are read-only.</p>
          </div>
        </div>

        {/* ── Right: grouped list ── */}
        <div className="palettes-right">

          <div className="palettes-toolbar">
            <span className="section-label">palette library</span>
          </div>

          {loading && (
            <div className="empty-state"><div className="spinner" /></div>
          )}

          {!loading && palettes.length === 0 && (
            <div className="empty-state">
              <p>no palettes found — add <code>.pal</code> files to <code>palettes/</code></p>
            </div>
          )}

          {!loading && SOURCE_ORDER.map(src => {
            const group = grouped[src]
            if (!group?.length) return null
            return (
              <div key={src} className="palettes-group">
                <div className="palettes-group-header">
                  <span className="section-label">{SOURCE_LABELS[src]}</span>
                  <span className="palettes-group-count">{group.length}</span>
                </div>
                <div className="palettes-group-list">
                  {group.map(p => (
                    <PaletteRow
                      key={p.name}
                      palette={p}
                      onDelete={handleDelete}
                      onDownload={handleDownload}
                    />
                  ))}
                </div>
              </div>
            )
          })}

        </div>

      </div>
    </div>
  )
}