import { useState, useEffect, useRef } from 'react'
import './ConvertTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { WalkAnimation } from '../components/WalkAnimation'
import { ResultCard } from '../components/ResultCard'
import { PaletteStrip } from '../components/PaletteStrip'
import { PalettePicker } from '../components/PalettePicker'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob, detectBgColor } from '../utils'
import { X, RefreshCw, Layers } from 'lucide-react'
import { BgColorPicker } from '../components/BgColorPicker'
import { Modal } from '../components/Modal'
import { ViewToggle } from '../components/ViewToggle'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

// ── Palette Management Modal ──────────────────────────────────────────────────

function PaletteModal({ palettes, selected, onChange, onReload, onUpload, onClose, reloading }) {
  const fileRef = useRef()

  const actions = (
    <>
      <button
        style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 8px', background: 'transparent', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11, cursor: 'pointer', transition: 'color 0.1s, border-color 0.1s' }}
        title="reload from disk"
        onClick={onReload}
        disabled={reloading}
      >
        <RefreshCw size={12} className={reloading ? 'spinning' : ''} /> reload
      </button>
    </>
  )

  const handleImportFile = async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    await fetch(`${API}/palettes/upload`, { method: 'POST', body: fd }).catch(() => {})
    onUpload()
  }

  return (
    <Modal title="manage palettes" onClose={onClose} size="lg" actions={actions}>
      <PalettePicker
        palettes={palettes}
        mode="multi"
        selected={selected}
        onChange={onChange}
        onImportFile={handleImportFile}
        showSelectAll={true}
      />
    </Modal>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function ConvertTab() {
  const [file, setFile]         = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [results, setResults]   = useState([])
  const [selected, setSelected] = useState(null)
  const [viewMode, setViewMode] = useState('grid')

  const [bgColor, setBgColor]   = useState(GBA_TRANSPARENT)
  const [bgMode, setBgMode]     = useState('auto')
  const [picking, setPicking]   = useState(false)

  const [palettes, setPalettes]           = useState([])
  const [selectedPalettes, setSelectedPalettes] = useState(new Set())
  const [reloading, setReloading]         = useState(false)
  const [showPaletteModal, setShowPaletteModal] = useState(false)

  const { loading, error, run } = useFetch()
  const isMounted = useRef(false)

  const fetchPalettes = async () => {
    const data = await fetch(`${API}/palettes`).then(r => r.json()).catch(() => [])
    setPalettes(data)
    setSelectedPalettes(prev => {
      const next = new Set(prev)
      data.forEach(p => { if (!next.has(p.name)) next.add(p.name) })
      return next
    })
  }

  useEffect(() => { fetchPalettes() }, [])

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
        setBgColor(detected); setBgMode('auto')
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
          onChange={setSelectedPalettes}
          onReload={handleReload}
          onUpload={async () => { await handleReload() }}
          onClose={() => setShowPaletteModal(false)}
          reloading={reloading}
        />
      )}

      <div className="convert-layout">
        <div className="convert-left">
          <DropZone onFile={handleFile} label="Drop your sprite" />

          {originalB64 && (
            <>
              <div className="field">
                <label className="field-label">transparent color (slot 0)</label>
                <BgColorPicker
                  color={bgColor} mode={bgMode}
                  onChange={({ color, mode }) => { setBgColor(color); setBgMode(mode) }}
                  onCommit={color => convert(file, color)}
                  showAuto={!!originalB64}
                  onAutoDetect={() => detectBgColor(originalB64)}
                  showPipette={!!originalB64}
                  picking={picking}
                  onPipetteToggle={() => setPicking(p => !p)}
                />
              </div>
              <div className="original-preview">
                <p className="section-label">
                  original
                  {picking && <span className="pick-hint"> · click to pick bg color</span>}
                </p>
                <ZoomableImage
                  src={originalB64} alt="original"
                  picking={picking}
                  onPick={hex => { setBgColor(hex); setBgMode('pick'); setPicking(false); convert(file, hex) }}
                />
              </div>
            </>
          )}

          {results.length > 0 && (
            <button className="btn-secondary" onClick={handleDownloadAll}>download all as zip</button>
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
            <span className="results-count">{results.length > 0 ? `${results.length} palettes` : ''}</span>
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
              {results.length > 0 && <ViewToggle value={viewMode} onChange={setViewMode} />}
            </div>
          </div>

          {results.length === 0 && !loading && (
            <div className="empty-state"><p>drop a sprite to see all palette conversions</p></div>
          )}
          {loading && <div className="empty-state"><div className="spinner" /><p>processing…</p></div>}

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