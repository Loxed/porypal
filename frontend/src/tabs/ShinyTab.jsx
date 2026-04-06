import { useState, useEffect, useRef } from 'react'
import './ShinyTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { PalettePicker } from '../components/PalettePicker'
import { Modal } from '../components/Modal'
import { ExportDropdown } from '../components/ExportDropdown'
import { remapToShinyPalette, detectBgColor, downloadBlob } from '../utils'
import { Download } from 'lucide-react'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

function fileToB64(file) {
  return new Promise(resolve => {
    const reader = new FileReader()
    reader.onload = e => resolve(e.target.result.split(',')[1])
    reader.readAsDataURL(file)
  })
}

function parsePalFile(text) {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  const colorLines = lines.slice(3)
  const colors = []
  for (const line of colorLines) {
    const parts = line.split(/\s+/)
    if (parts.length >= 3) {
      const r = parseInt(parts[0]), g = parseInt(parts[1]), b = parseInt(parts[2])
      if (!isNaN(r) && !isNaN(g) && !isNaN(b))
        colors.push(`#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`)
    }
  }
  return colors
}

// ── Palette picker modal ──────────────────────────────────────────────────────

function PalettePickerModal({ palettes, currentName, onPick, onClose }) {
  const [localPalettes, setLocalPalettes] = useState(palettes)

  const handleImportFile = (file) => {
    const reader = new FileReader()
    reader.onload = ev => {
      const colors = parsePalFile(ev.target.result)
      if (colors.length > 0) {
        const p = { name: file.name, path: file.name, folder: null, colors, count: colors.length, is_default: false, source: 'user' }
        onPick(p)
        onClose()
      }
    }
    reader.readAsText(file)
  }

  return (
    <Modal title="select palette" onClose={onClose}>
      <PalettePicker
        palettes={localPalettes}
        mode="single"
        selected={currentName}
        onChange={name => {
          const p = localPalettes.find(x => x.name === name)
          if (p) { onPick(p); onClose() }
        }}
        onImportFile={handleImportFile}
        showSelectAll={false}
      />
    </Modal>
  )
}

function PalPickRow({ label, palette, onPick }) {
  return (
    <div className="field">
      <label className="field-label">{label}</label>
      <div className="pal-pick-row">
        <span className="pal-pick-name">{palette ? palette.name.replace(/\.pal$/, '').split('/').pop() : 'none selected'}</span>
        <button className="pal-pick-btn" onClick={onPick}>pick</button>
      </div>
      {palette && (
        <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
      )}
    </div>
  )
}

// ── Mode 1: Apply shiny palette ───────────────────────────────────────────────

function ApplyShinyMode({ palettes }) {
  const [spriteFile, setSpriteFile]       = useState(null)
  const [spriteB64, setSpriteB64]         = useState(null)
  const [outputName, setOutputName]       = useState('')
  const [normalPal, setNormalPal]         = useState(null)
  const [shinyPal, setShinyPal]           = useState(null)
  const [normalPreview, setNormalPreview] = useState(null)
  const [shinyPreview, setShinyPreview]   = useState(null)
  const [pickingFor, setPickingFor]       = useState(null)
  const [downloading, setDownloading]     = useState(false)

  useEffect(() => {
    if (!spriteB64 || !normalPal) { setNormalPreview(null); return }
    remapToShinyPalette(spriteB64, normalPal.colors, normalPal.colors).then(setNormalPreview)
  }, [spriteB64, normalPal])

  useEffect(() => {
    if (!spriteB64 || !normalPal || !shinyPal) { setShinyPreview(null); return }
    remapToShinyPalette(spriteB64, normalPal.colors, shinyPal.colors).then(setShinyPreview)
  }, [spriteB64, normalPal, shinyPal])

  const handleSprite = async (f) => {
    setSpriteFile(f)
    setSpriteB64(await fileToB64(f))
    setOutputName(f.name.replace(/\.[^.]+$/, ''))
  }

  const handleDownloadZip = async () => {
    if (!spriteFile || !normalPal || !shinyPal || !outputName.trim()) return
    setDownloading(true)
    try {
      const fd = new FormData()
      fd.append('sprite_file', spriteFile)
      fd.append('normal_pal', JSON.stringify(normalPal.colors))
      fd.append('shiny_pal', JSON.stringify(shinyPal.colors))
      fd.append('normal_pal_name', normalPal.name.replace('.pal', ''))
      fd.append('shiny_pal_name', shinyPal.name.replace('.pal', ''))
      fd.append('sprite_name', outputName.trim())
      const res = await fetch(`${API}/shiny/apply/download`, { method: 'POST', body: fd })
      if (!res.ok) return
      downloadBlob(await res.blob(), `${outputName.trim()}.zip`)
    } finally { setDownloading(false) }
  }

  return (
    <>
      {pickingFor && (
        <PalettePickerModal
          palettes={palettes}
          currentName={pickingFor === 'normal' ? normalPal?.name : shinyPal?.name}
          onPick={p => pickingFor === 'normal' ? setNormalPal(p) : setShinyPal(p)}
          onClose={() => setPickingFor(null)}
        />
      )}
      <div className="shiny-layout">
        <div className="shiny-left">
          <DropZone onFile={handleSprite} label="Drop sprite" />
          {spriteFile && (
            <div className="field">
              <label className="field-label">output name</label>
              <input
                className="field-input"
                value={outputName}
                onChange={e => setOutputName(e.target.value)}
                spellCheck={false}
                placeholder="shiny_sprite"
              />
              <span className="shiny-field-hint">used for the downloaded zip and embedded sprite filenames</span>
            </div>
          )}
          <PalPickRow label="normal palette" palette={normalPal} onPick={() => setPickingFor('normal')} />
          <PalPickRow label="shiny palette"  palette={shinyPal}  onPick={() => setPickingFor('shiny')} />
        </div>
        <div className="shiny-right">
          {!spriteB64 && <div className="empty-state">drop a sprite and select palettes to preview</div>}
          {spriteB64 && (
            <div className="shiny-preview-stack">
              <div className="shiny-previews">
                <div className="shiny-preview-section">
                  <p className="section-label">normal</p>
                  {normalPreview
                    ? <ZoomableImage src={normalPreview} alt="normal" />
                    : <div className="empty-state" style={{ minHeight: 120 }}>pick normal palette</div>}
                  {normalPal && <PaletteStrip colors={normalPal.colors} usedIndices={normalPal.colors.map((_,i) => i)} checkSize="100%" />}
                </div>
                <div className="shiny-preview-section">
                  <p className="section-label">shiny</p>
                  {shinyPreview
                    ? <ZoomableImage src={shinyPreview} alt="shiny" />
                    : <div className="empty-state" style={{ minHeight: 120 }}>pick shiny palette</div>}
                  {shinyPal && <PaletteStrip colors={shinyPal.colors} usedIndices={shinyPal.colors.map((_,i) => i)} checkSize="100%" />}
                </div>
              </div>
              <button
                className="btn-primary shiny-download-btn"
                disabled={!spriteFile || !normalPal || !shinyPal || !shinyPreview || downloading || !outputName.trim()}
                onClick={handleDownloadZip}
              >
                <Download size={13} /> {downloading ? 'downloading…' : `Download '${outputName.trim()}.zip'`}
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ── Mode 2: Extract matched palettes ─────────────────────────────────────────

function ExtractMatchedMode() {
  const [normalFile, setNormalFile]       = useState(null)
  const [shinyFile, setShinyFile]         = useState(null)
  const [normalB64, setNormalB64]         = useState(null)
  const [shinyB64, setShinyB64]           = useState(null)
  const [outputName, setOutputName]       = useState('')
  const [nColors, setNColors]             = useState(15)
  const [bgColor, setBgColor]             = useState(GBA_TRANSPARENT)
  const [result, setResult]               = useState(null)
  const [loading, setLoading]             = useState(false)
  const [downloading, setDownloading]     = useState(false)
  const [error, setError]                 = useState(null)
  const [normalPreview, setNormalPreview] = useState(null)
  const [shinyPreview, setShinyPreview]   = useState(null)

  useEffect(() => {
    if (!result || !normalB64) return
    remapToShinyPalette(normalB64, result.normal.colors, result.normal.colors).then(setNormalPreview)
    remapToShinyPalette(normalB64, result.normal.colors, result.shiny.colors).then(setShinyPreview)
  }, [result, normalB64])

  const handleNormalFile = async (f) => {
    setNormalFile(f); setResult(null); setNormalPreview(null); setShinyPreview(null)
    const b64 = await fileToB64(f)
    setNormalB64(b64)
    setBgColor(await detectBgColor(b64))
    setOutputName(`${f.name.replace(/\.[^.]+$/, '')}_shiny_pair`)
  }

  const handleShinyFile = async (f) => {
    setShinyFile(f); setResult(null); setNormalPreview(null); setShinyPreview(null)
    setShinyB64(await fileToB64(f))
  }

  const handleExtract = async () => {
    if (!normalFile || !shinyFile) return
    setLoading(true); setError(null); setResult(null)
    try {
      const fd = new FormData()
      fd.append('normal_file', normalFile); fd.append('shiny_file', shinyFile)
      fd.append('n_colors', nColors); fd.append('bg_color', bgColor)
      const res = await fetch(`${API}/shiny/extract-matched`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      setResult(await res.json())
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const handleDownloadZip = async () => {
    if (!normalFile || !shinyFile || !outputName.trim()) return
    setDownloading(true)
    try {
      const fd = new FormData()
      fd.append('normal_file', normalFile); fd.append('shiny_file', shinyFile)
      fd.append('n_colors', nColors); fd.append('bg_color', bgColor)
      const res = await fetch(`${API}/shiny/extract-matched/download`, { method: 'POST', body: fd })
      if (!res.ok) return
      downloadBlob(await res.blob(), `${outputName.trim()}.zip`)
    } finally { setDownloading(false) }
  }

  return (
    <div className="shiny-layout">
      <div className="shiny-left">
        <div className="sprite-pair">
          <span className="sprite-pair-label">normal sprite</span>
          <DropZone onFile={handleNormalFile} label="drop normal sprite" />
          {normalB64 && <div className="sprite-thumb"><img src={`data:image/png;base64,${normalB64}`} alt="normal" /></div>}
        </div>
        <div className="sprite-pair">
          <span className="sprite-pair-label">shiny sprite</span>
          <DropZone onFile={handleShinyFile} label="drop shiny sprite" />
          {shinyB64 && <div className="sprite-thumb"><img src={`data:image/png;base64,${shinyB64}`} alt="shiny" /></div>}
        </div>
        {(normalFile || shinyFile) && (
          <div className="field">
            <label className="field-label">output name</label>
            <input
              className="field-input"
              value={outputName}
              onChange={e => setOutputName(e.target.value)}
              spellCheck={false}
              placeholder="sprite_shiny_pair"
            />
            <span className="shiny-field-hint">used for the downloaded zip filename</span>
          </div>
        )}
        <div className="field">
          <label className="field-label">colors (max 15)</label>
          <input type="number" className="field-input" min={1} max={15} value={nColors}
            onChange={e => setNColors(Number(e.target.value))} />
        </div>
        <div className="field">
          <label className="field-label">bg color</label>
          <div className="bg-color-row">
            <div className="bg-swatch" style={{ background: bgColor }} />
            <input className="field-input field-mono" value={bgColor}
              onChange={e => setBgColor(e.target.value)} maxLength={7} placeholder="#73C5A4" />
          </div>
        </div>
        <button className="btn-primary" disabled={!normalFile || !shinyFile || loading} onClick={handleExtract}>
          {loading ? 'extracting…' : 'extract matched palettes'}
        </button>
        {error && <p className="error-msg">{error}</p>}
      </div>

      <div className="shiny-right">
        {!result && <div className="empty-state">drop both sprites and extract to see matched palettes</div>}
        {result && (
          <div className="shiny-preview-stack">
            <div className="shiny-previews">
              <div className="shiny-preview-section">
                <div className="shiny-preview-header">
                  <p className="section-label">normal — {result.normal.colors.length} colors</p>
                  <ExportDropdown name={result.normal.name} palContent={result.normal.pal_content} />
                </div>
                {normalPreview && <ZoomableImage src={normalPreview} alt="normal preview" />}
                <PaletteStrip colors={result.normal.colors} usedIndices={result.normal.colors.map((_,i)=>i)} checkSize="100%" />
              </div>
              <div className="shiny-preview-section">
                <div className="shiny-preview-header">
                  <p className="section-label">shiny — {result.shiny.colors.length} colors</p>
                  <ExportDropdown name={result.shiny.name + '_shiny'} palContent={result.shiny.pal_content} />
                </div>
                {shinyPreview && <ZoomableImage src={shinyPreview} alt="shiny preview" />}
                <PaletteStrip colors={result.shiny.colors} usedIndices={result.shiny.colors.map((_,i)=>i)} checkSize="100%" />
              </div>
            </div>
            <button
              className="btn-primary shiny-download-btn"
              disabled={downloading || !outputName.trim()}
              onClick={handleDownloadZip}
            >
              <Download size={13} /> {downloading ? 'downloading…' : `Download '${outputName.trim()}.zip'`}
            </button>
            </div>
        )}
      </div>
    </div>
  )
}

// ── Tab root ──────────────────────────────────────────────────────────────────

export function ShinyTab() {
  const [mode, setMode]         = useState('apply')
  const [palettes, setPalettes] = useState([])

  useEffect(() => {
    fetch(`${API}/palettes`).then(r => r.json()).then(setPalettes).catch(() => {})
  }, [])

  return (
    <div className="tab-content">
      <div style={{ marginBottom: 20 }}>
        <div className="mode-toggle">
          <button className={`mode-btn ${mode === 'apply' ? 'active' : ''}`} onClick={() => setMode('apply')}>
            Create shiny sprite
            <div style={{ fontSize: 9, opacity: 0.8, marginTop: 2 }}>sprite.png + normal.pal + shiny.pal = shiny_sprite.png</div>
          </button>
          <button className={`mode-btn ${mode === 'extract' ? 'active' : ''}`} onClick={() => setMode('extract')}>
            Create palette pair
            <div style={{ fontSize: 9, opacity: 0.8, marginTop: 2 }}>normal.png + shiny.png = normal.pal + shiny.pal</div>
          </button>
        </div>
      </div>
      {mode === 'apply'   && <ApplyShinyMode palettes={palettes} />}
      {mode === 'extract' && <ExtractMatchedMode />}
    </div>
  )
}
