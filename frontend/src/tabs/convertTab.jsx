import { useState, useEffect, useRef } from 'react'
import './ConvertTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { WalkAnimation } from '../components/WalkAnimation'
import { ResultCard } from '../components/ResultCard'
import { PaletteStrip } from '../components/PaletteStrip'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob, detectBgColor} from '../utils'
import { X, Upload, Trash2, RefreshCw, Layers, Grid, List } from 'lucide-react'
import { BgColorPicker } from '../components/BgColorPicker'
import { Modal } from '../components/Modal'


const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

function GridIcon() {
  return <Grid size={12} fill="currentColor" />
}

function ListIcon() {
  return <List size={12} fill="currentColor" />
}

// ---- Palette Management Modal ----
function PaletteModal({ palettes, selected, onToggle, onSelectAll, onDeselectAll, onReload, onUpload, onDelete, onClose, reloading }) {
  const fileRef = useRef()
  const allSelected = palettes.length > 0 && palettes.every(p => selected.has(p.name))

  const actions = (
    <>
      <button className="icon-btn" title="reload from disk" onClick={onReload} disabled={reloading}>
        <RefreshCw size={12} className={reloading ? 'spinning' : ''} />
      </button>
      <button className="icon-btn" title="upload .pal files" onClick={() => fileRef.current?.click()}>
        <Upload size={12} />
      </button>
      <input ref={fileRef} type="file" accept=".pal" multiple className="hidden-input"
        onChange={e => { onUpload(e.target.files); e.target.value = '' }} />
    </>
  )

  return (
    <Modal title="manage palettes" onClose={onClose} size="lg" actions={actions}>
      {palettes.length === 0 ? (
        <p className="palette-empty">
          no palettes loaded — drop <code>.pal</code> files into <code>palettes/</code> or upload above
        </p>
      ) : (
        <>
          <div className="palette-select-all">
            <label className="palette-checkbox-row">
              <input type="checkbox" checked={allSelected}
                onChange={e => e.target.checked ? onSelectAll() : onDeselectAll()} />
              <span>{allSelected ? 'deselect all' : 'select all'}</span>
              <span className="palette-count-badge">{selected.size}/{palettes.length} active</span>
            </label>
          </div>
          <div className="palette-list">
            {palettes.map(p => (
              <div key={p.name} className={`palette-row ${selected.has(p.name) ? 'active' : ''}`}>
                <label className="palette-row-label">
                  <input type="checkbox" checked={selected.has(p.name)} onChange={() => onToggle(p.name)} />
                  <div className="palette-row-info">
                    <span className="palette-name">{p.name.replace('.pal', '')}</span>
                    <PaletteStrip colors={p.colors} usedIndices={p.colors.map((_, i) => i)} />
                  </div>
                </label>
                <button className="icon-btn icon-btn--danger" title="delete palette" onClick={() => onDelete(p.name)}>
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </Modal>
  )
}

// ---- Main ----
export function ConvertTab() {
  const [file, setFile] = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [viewMode, setViewMode] = useState('grid')

  const [bgColor, setBgColor] = useState(GBA_TRANSPARENT)
  const [bgMode, setBgMode]   = useState('auto')

  const [palettes, setPalettes] = useState([])
  const [selectedPalettes, setSelectedPalettes] = useState(new Set())
  const [reloading, setReloading] = useState(false)
  const [showPaletteModal, setShowPaletteModal] = useState(false)

  const { loading, error, run } = useFetch()

  const fetchPalettes = async () => {
    const data = await fetch(`${API}/palettes`).then(r => r.json()).catch(() => [])
    setPalettes(data)
    setSelectedPalettes(prev => {
      const next = new Set(prev)
      data.forEach(p => { if (!next.has(p.name)) next.add(p.name) })
      return next
    })
  }

  const isMounted = useRef(false)

  useEffect(() => { fetchPalettes() }, [])

  // Auto-reprocess whenever the palette selection changes, but only after
  // a file has been loaded and after the initial mount settles.
  useEffect(() => {
    if (!isMounted.current) { isMounted.current = true; return }
    if (file) convert(file)
  }, [selectedPalettes])

  const convert = async (f, overrideBg) => {
    if (selectedPalettes.size === 0) return
    const activeBg = overrideBg ?? bgColor
    const fd = new FormData()
    fd.append('file', f)
    if (activeBg) fd.append('bg_color', activeBg)
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
    const reader = new FileReader()
    reader.onload = e => {
      const b64 = e.target.result.split(',')[1]
      detectBgColor(b64).then(detected => {
        setBgColor(detected)
        setBgMode('auto')
        convert(f, detected)
      })
    }
    reader.readAsDataURL(f)
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
    fd.append('file', file)
    fd.append('palette_name', paletteName)
    if (bgColor) fd.append('bg_color', bgColor)
    const res = await fetch(`${API}/convert/download`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_${paletteName.replace('.pal', '')}.png`)
  }

  const handleDownloadAll = async () => {
    const fd = new FormData()
    fd.append('file', file)
    if (bgColor) fd.append('bg_color', bgColor)
    // derive names from what's currently shown — always matches the UI exactly
    fd.append('palette_names', JSON.stringify(results.map(r => r.palette_name)))
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
            <>
              {/* ── Transparent color picker ── */}
              <div className="field">
                <label className="field-label">transparent color (slot 0)</label>
                <BgColorPicker
                  color={bgColor}
                  mode={bgMode}
                  onChange={({ color, mode }) => { setBgColor(color); setBgMode(mode) }}
                  onCommit={color => convert(file, color)}
                  showAuto={!!originalB64}
                  onAutoDetect={() => detectBgColor(originalB64)}
                />
              </div>

              {/* ── Original preview ── */}
              <div className="original-preview">
                <p className="section-label">original</p>
                <ZoomableImage src={originalB64} alt="original" />
              </div>
            </>
          )}

          {results.length > 0 && (
            <button className="btn-secondary" onClick={handleDownloadAll}>
              download all as zip
            </button>
          )}
          <button
            className="btn-ghost-subtle"
            disabled={!file || loading || selectedPalettes.size === 0}
            onClick={() => convert(file)}
          >
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
                  <button
                    className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                    onClick={() => setViewMode('grid')}
                    title="grid view"
                  ><GridIcon /></button>
                  <button
                    className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                    onClick={() => setViewMode('list')}
                    title="list view"
                  ><ListIcon /></button>
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