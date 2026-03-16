import { useState, useEffect, useRef } from 'react'
import './ConvertTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { WalkAnimation } from '../components/WalkAnimation'
import { ResultCard } from '../components/ResultCard'
import { PaletteStrip } from '../components/PaletteStrip'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob } from '../utils'
import { X, Upload, Trash2, RefreshCw, Layers } from 'lucide-react'

const API = '/api'

function GridIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="0" y="0" width="6" height="6" rx="1"/>
      <rect x="8" y="0" width="6" height="6" rx="1"/>
      <rect x="0" y="8" width="6" height="6" rx="1"/>
      <rect x="8" y="8" width="6" height="6" rx="1"/>
    </svg>
  )
}

function ListIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="0" y="1" width="14" height="3" rx="1"/>
      <rect x="0" y="6" width="14" height="3" rx="1"/>
      <rect x="0" y="11" width="14" height="3" rx="1"/>
    </svg>
  )
}

// ---- Palette Management Modal ----
function PaletteModal({ palettes, selected, onToggle, onSelectAll, onDeselectAll, onReload, onUpload, onDelete, onClose, reloading }) {
  const fileRef = useRef()
  const allSelected = palettes.length > 0 && palettes.every(p => selected.has(p.name))

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box modal-palettes" onClick={e => e.stopPropagation()}>

        <div className="modal-header">
          <span className="modal-title">manage palettes</span>
          <div className="modal-header-actions">
            <button
              className="icon-btn"
              title="reload from disk"
              onClick={onReload}
              disabled={reloading}
            >
              <RefreshCw size={12} className={reloading ? 'spinning' : ''} />
            </button>
            <button
              className="icon-btn"
              title="upload .pal files"
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={12} />
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".pal"
              multiple
              className="hidden-input"
              onChange={e => { onUpload(e.target.files); e.target.value = '' }}
            />
            <button className="modal-close" onClick={onClose}><X size={16} /></button>
          </div>
        </div>

        <div className="modal-body">
          {palettes.length === 0 ? (
            <p className="palette-empty">
              no palettes loaded — drop <code>.pal</code> files into <code>palettes/</code> or upload above
            </p>
          ) : (
            <>
              <div className="palette-select-all">
                <label className="palette-checkbox-row">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={e => e.target.checked ? onSelectAll() : onDeselectAll()}
                  />
                  <span>{allSelected ? 'deselect all' : 'select all'}</span>
                  <span className="palette-count-badge">{selected.size}/{palettes.length} active</span>
                </label>
              </div>

              <div className="palette-list">
                {palettes.map(p => (
                  <div key={p.name} className={`palette-row ${selected.has(p.name) ? 'active' : ''}`}>
                    <label className="palette-row-label">
                      <input
                        type="checkbox"
                        checked={selected.has(p.name)}
                        onChange={() => onToggle(p.name)}
                      />
                      <div className="palette-row-info">
                        <span className="palette-name">{p.name.replace('.pal', '')}</span>
                        <PaletteStrip colors={p.colors} usedIndices={p.colors.map((_, i) => i)} />
                      </div>
                    </label>
                    <button
                      className="icon-btn icon-btn--danger"
                      title="delete palette"
                      onClick={() => onDelete(p.name)}
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

      </div>
    </div>
  )
}

// ---- Main ----
export function ConvertTab() {
  const [file, setFile] = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [isOWSprite, setIsOWSprite] = useState(false)

  const [palettes, setPalettes] = useState([])
  const [selectedPalettes, setSelectedPalettes] = useState(new Set())
  const [reloading, setReloading] = useState(false)
  const [showPaletteModal, setShowPaletteModal] = useState(false)

  const { loading, error, run } = useFetch()

  const fetchPalettes = async () => {
    const data = await fetch(`${API}/palettes`).then(r => r.json()).catch(() => [])
    setPalettes(data)
    // Auto-select any newly discovered palettes
    setSelectedPalettes(prev => {
      const next = new Set(prev)
      data.forEach(p => { if (!next.has(p.name)) next.add(p.name) })
      return next
    })
  }

  useEffect(() => { fetchPalettes() }, [])

  useEffect(() => {
    if (!originalB64) { setIsOWSprite(false); return }
    const img = new window.Image()
    img.onload = () => setIsOWSprite(img.width / img.height >= 7.5 && img.width / img.height <= 10.5)
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  const convert = async (f) => {
    if (selectedPalettes.size === 0) return
    const fd = new FormData()
    fd.append('file', f)
    const data = await run(async () => {
      const res = await fetch(`${API}/convert`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) {
      setOriginalB64(data.original)
      const filtered = data.results.filter(r => selectedPalettes.has(r.palette_name))
      setResults(filtered)
      setSelected(filtered.findIndex(r => r.best))
    }
  }

  const handleFile = (f) => {
    setFile(f); setResults([]); setSelected(null); setOriginalB64(null)
    convert(f)
  }

  const handleReload = async () => {
    setReloading(true)
    await fetch(`${API}/palettes/reload`, { method: 'POST' })
    await fetchPalettes()
    setReloading(false)
  }

  const handleUpload = async (files) => {
    await Promise.all(Array.from(files).map(async (f) => {
      const fd = new FormData()
      fd.append('file', f)
      await fetch(`${API}/palettes/upload`, { method: 'POST', body: fd }).catch(() => {})
    }))
    await handleReload()
  }

  const handleDelete = async (name) => {
    await fetch(`${API}/palettes/${encodeURIComponent(name)}`, { method: 'DELETE' }).catch(() => {})
    setSelectedPalettes(prev => { const n = new Set(prev); n.delete(name); return n })
    await fetchPalettes()
  }

  const handleToggle = (name) => {
    setSelectedPalettes(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const handleDownload = async (paletteName) => {
    const fd = new FormData()
    fd.append('file', file); fd.append('palette_name', paletteName)
    const res = await fetch(`${API}/convert/download`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_${paletteName.replace('.pal', '')}.png`)
  }

  const handleDownloadAll = async () => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API}/convert/download-all`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_all_palettes.zip`)
  }

  return (
    <div className="tab-content">
      {showPaletteModal && (
        <PaletteModal
          palettes={palettes}
          selected={selectedPalettes}
          onToggle={handleToggle}
          onSelectAll={() => setSelectedPalettes(new Set(palettes.map(p => p.name)))}
          onDeselectAll={() => setSelectedPalettes(new Set())}
          onReload={handleReload}
          onUpload={handleUpload}
          onDelete={handleDelete}
          onClose={() => setShowPaletteModal(false)}
          reloading={reloading}
        />
      )}

      <div className="convert-layout">

        <div className="convert-left">
          <DropZone onFile={handleFile} label="Drop your sprite" />

          {originalB64 && (
            <div className="original-preview">
              <p className="section-label">original</p>
              <ZoomableImage src={originalB64} alt="original" />
              {isOWSprite && <WalkAnimation spriteB64={originalB64} />}
            </div>
          )}

          {results.length > 0 && (
            <button className="btn-secondary" onClick={handleDownloadAll}>
              download all as zip
            </button>
          )}
          <button className="btn-ghost-subtle" disabled={!file || loading || selectedPalettes.size === 0} onClick={() => convert(file)}>
            {loading ? 'converting…' : '↺ re-process'}
          </button>
          {error && <p className="error-msg">{error}</p>}
        </div>

        <div className="convert-right">
          <div className="results-toolbar">
            <span className="results-count">
              {results.length > 0 ? `${results.length} palettes` : ''}
            </span>
            <div className="toolbar-right">
              <button
                className={`palette-mgr-btn ${selectedPalettes.size < palettes.length ? 'filtered' : ''}`}
                onClick={() => setShowPaletteModal(true)}
                title="manage palettes"
              >
                <Layers size={12} />
                <span>palettes</span>
                <span className="palette-mgr-badge">{selectedPalettes.size}/{palettes.length}</span>
              </button>
              {results.length > 0 && (
                <div className="view-toggle">
                  <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                    onClick={() => setViewMode('grid')} title="grid view"><GridIcon /></button>
                  <button className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                    onClick={() => setViewMode('list')} title="list view"><ListIcon /></button>
                </div>
              )}
            </div>
          </div>

          {results.length === 0 && !loading && (
            <div className="empty-state"><p>drop a sprite to see all palette conversions</p></div>
          )}
          {loading && (
            <div className="empty-state"><div className="spinner" /><p>processing…</p></div>
          )}

          <div className={viewMode === 'grid' ? 'results-grid' : 'results-list'}>
            {results.map((r, i) => (
              <ResultCard
                key={r.palette_name}
                result={r}
                selected={selected === i}
                onSelect={() => setSelected(i)}
                onDownload={handleDownload}
                listMode={viewMode === 'list'}
              />
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}