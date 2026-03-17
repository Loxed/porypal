import { useState, useEffect, useRef } from 'react'
import './ShinyTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { remapToShinyPalette, detectBgColor } from '../utils'
import { X, Download, Check } from 'lucide-react'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fileToB64(file) {
  return new Promise(resolve => {
    const reader = new FileReader()
    reader.onload = e => resolve(e.target.result.split(',')[1])
    reader.readAsDataURL(file)
  })
}

function downloadPal(palContent, filename) {
  const blob = new Blob([palContent], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename.endsWith('.pal') ? filename : `${filename}.pal`
  a.click()
}

// ---------------------------------------------------------------------------
// Palette picker modal
// ---------------------------------------------------------------------------
function PalettePickerModal({ palettes, current, onPick, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">select palette</span>
          <button className="modal-close" onClick={onClose}><X size={16}/></button>
        </div>
        <div className="modal-body">
          <div className="pal-select-list">
            {palettes.map(p => (
              <div
                key={p.name}
                className={`pal-select-row ${current === p.name ? 'active' : ''}`}
                onClick={() => { onPick(p); onClose() }}
              >
                <span className="pal-select-row-name">{p.name.replace('.pal', '')}</span>
                <div className="pal-select-row-strip">
                  <PaletteStrip colors={p.colors} usedIndices={p.colors.map((_, i) => i)} checkSize="50%" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Export button with save-to-library support
// ---------------------------------------------------------------------------
function ExportPalBtn({ label, palContent, filename }) {
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    try {
      const fd = new FormData()
      fd.append('name', filename)
      fd.append('pal_content', palContent)
      const res = await fetch(`${API}/extract/save`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error()
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { /* ignore */ }
  }

  return (
    <div style={{ display: 'flex', gap: 6 }}>
      <button className="btn-secondary" onClick={() => downloadPal(palContent, filename)}>
        <Download size={11} /> {label}
      </button>
      <button className="btn-secondary" onClick={handleSave}>
        {saved ? <><Check size={11} /> saved</> : 'save to library'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Mode 1: Apply shiny palette to sprite
// ---------------------------------------------------------------------------
function ApplyShinyMode({ palettes }) {
  const [spriteB64, setSpriteB64]       = useState(null)
  const [bgColor, setBgColor]           = useState(GBA_TRANSPARENT)
  const [normalPal, setNormalPal]       = useState(null)
  const [shinyPal, setShinyPal]         = useState(null)
  const [normalPreview, setNormalPreview] = useState(null)
  const [shinyPreview, setShinyPreview]   = useState(null)
  const [pickingFor, setPickingFor]     = useState(null) // 'normal' | 'shiny' | null

  // Recompute previews whenever sprite or palettes change
  useEffect(() => {
    if (!spriteB64 || !normalPal) { setNormalPreview(null); return }
    remapToShinyPalette(spriteB64, normalPal.colors, normalPal.colors).then(setNormalPreview)
  }, [spriteB64, normalPal])

  useEffect(() => {
    if (!spriteB64 || !normalPal || !shinyPal) { setShinyPreview(null); return }
    remapToShinyPalette(spriteB64, normalPal.colors, shinyPal.colors).then(setShinyPreview)
  }, [spriteB64, normalPal, shinyPal])

  const handleSprite = async (f) => {
    const b64 = await fileToB64(f)
    setSpriteB64(b64)
    const detected = await detectBgColor(b64)
    setBgColor(detected)
  }

  return (
    <>
      {pickingFor && (
        <PalettePickerModal
          palettes={palettes}
          current={pickingFor === 'normal' ? normalPal?.name : shinyPal?.name}
          onPick={p => pickingFor === 'normal' ? setNormalPal(p) : setShinyPal(p)}
          onClose={() => setPickingFor(null)}
        />
      )}

      <div className="shiny-layout">
        {/* ── Left ── */}
        <div className="shiny-left">
          <DropZone onFile={handleSprite} label="Drop sprite" />

          <div className="field">
            <label className="field-label">normal palette</label>
            <div className="pal-pick-row">
              <span className="pal-pick-name">
                {normalPal ? normalPal.name.replace('.pal','') : 'none selected'}
              </span>
              <button className="pal-pick-btn" onClick={() => setPickingFor('normal')}>
                pick
              </button>
            </div>
            {normalPal && (
              <PaletteStrip
                colors={normalPal.colors}
                usedIndices={normalPal.colors.map((_,i) => i)}
                checkSize="50%"
              />
            )}
          </div>

          <div className="field">
            <label className="field-label">shiny palette</label>
            <div className="pal-pick-row">
              <span className="pal-pick-name">
                {shinyPal ? shinyPal.name.replace('.pal','') : 'none selected'}
              </span>
              <button className="pal-pick-btn" onClick={() => setPickingFor('shiny')}>
                pick
              </button>
            </div>
            {shinyPal && (
              <PaletteStrip
                colors={shinyPal.colors}
                usedIndices={shinyPal.colors.map((_,i) => i)}
                checkSize="50%"
              />
            )}
          </div>
        </div>

        {/* ── Right ── */}
        <div className="shiny-right">
          {!spriteB64 && (
            <div className="empty-state">drop a sprite and select palettes to preview</div>
          )}

          {spriteB64 && (
            <div className="shiny-previews">
              <div className="shiny-preview-section">
                <p className="section-label">normal</p>
                {normalPreview
                  ? <ZoomableImage src={normalPreview} alt="normal" />
                  : <div className="empty-state" style={{ minHeight: 120 }}>pick normal palette</div>
                }
                {normalPal && (
                  <PaletteStrip
                    colors={normalPal.colors}
                    usedIndices={normalPal.colors.map((_,i) => i)}
                    checkSize="100%"
                  />
                )}
              </div>

              <div className="shiny-preview-section">
                <p className="section-label">shiny</p>
                {shinyPreview
                  ? <ZoomableImage src={shinyPreview} alt="shiny" />
                  : <div className="empty-state" style={{ minHeight: 120 }}>pick shiny palette</div>
                }
                {shinyPal && (
                  <PaletteStrip
                    colors={shinyPal.colors}
                    usedIndices={shinyPal.colors.map((_,i) => i)}
                    checkSize="100%"
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Mode 2: Extract matched palettes from normal + shiny sprites
// ---------------------------------------------------------------------------
function ExtractMatchedMode() {
  const [normalFile, setNormalFile]   = useState(null)
  const [shinyFile, setShinyFile]     = useState(null)
  const [normalB64, setNormalB64]     = useState(null)
  const [shinyB64, setShinyB64]       = useState(null)
  const [nColors, setNColors]         = useState(15)
  const [bgColor, setBgColor]         = useState(GBA_TRANSPARENT)
  const [result, setResult]           = useState(null)
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)

  // Preview the extracted palettes applied to the sprites
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
    const detected = await detectBgColor(b64)
    setBgColor(detected)
  }

  const handleShinyFile = async (f) => {
    setShinyFile(f); setResult(null); setNormalPreview(null); setShinyPreview(null)
    const b64 = await fileToB64(f)
    setShinyB64(b64)
  }

  const handleExtract = async () => {
    if (!normalFile || !shinyFile) return
    setLoading(true); setError(null); setResult(null)
    try {
      const fd = new FormData()
      fd.append('normal_file', normalFile)
      fd.append('shiny_file', shinyFile)
      fd.append('n_colors', nColors)
      fd.append('bg_color', bgColor)
      const res = await fetch(`${API}/shiny/extract-matched`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="shiny-layout">
      {/* ── Left ── */}
      <div className="shiny-left">
        <div className="sprite-pair">
          <span className="sprite-pair-label">normal sprite</span>
          <DropZone onFile={handleNormalFile} label="drop normal sprite" />
          {normalB64 && (
            <div className="sprite-thumb">
              <img src={`data:image/png;base64,${normalB64}`} alt="normal" />
            </div>
          )}
        </div>

        <div className="sprite-pair">
          <span className="sprite-pair-label">shiny sprite</span>
          <DropZone onFile={handleShinyFile} label="drop shiny sprite" />
          {shinyB64 && (
            <div className="sprite-thumb">
              <img src={`data:image/png;base64,${shinyB64}`} alt="shiny" />
            </div>
          )}
        </div>

        <div className="field">
          <label className="field-label">colors (max 15)</label>
          <input
            type="number"
            className="field-input"
            min={1} max={15}
            value={nColors}
            onChange={e => setNColors(Number(e.target.value))}
          />
        </div>

        <div className="field">
          <label className="field-label">bg color</label>
          <div className="bg-color-row">
            <div className="bg-swatch" style={{ background: bgColor }} />
            <input
              className="field-input field-mono"
              value={bgColor}
              onChange={e => setBgColor(e.target.value)}
              maxLength={7}
              placeholder="#73C5A4"
            />
          </div>
        </div>

        <button
          className="btn-primary"
          disabled={!normalFile || !shinyFile || loading}
          onClick={handleExtract}
        >
          {loading ? 'extracting…' : 'extract matched palettes'}
        </button>

        {error && <p className="error-msg">{error}</p>}

        {result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <ExportPalBtn
              label="download normal .pal"
              palContent={result.normal.pal_content}
              filename={result.normal.name}
            />
            <ExportPalBtn
              label="download shiny .pal"
              palContent={result.shiny.pal_content}
              filename={`${result.shiny.name}_shiny`}
            />
          </div>
        )}
      </div>

      {/* ── Right ── */}
      <div className="shiny-right">
        {!result && (
          <div className="empty-state">
            drop both sprites and extract to see matched palettes
          </div>
        )}

        {result && (
          <div className="shiny-previews">
            <div className="shiny-preview-section">
              <p className="section-label">normal — {result.normal.colors.length} colors</p>
              {normalPreview && <ZoomableImage src={normalPreview} alt="normal preview" />}
              <PaletteStrip
                colors={result.normal.colors}
                usedIndices={result.normal.colors.map((_,i) => i)}
                checkSize="100%"
              />
            </div>

            <div className="shiny-preview-section">
              <p className="section-label">shiny — {result.shiny.colors.length} colors</p>
              {shinyPreview && <ZoomableImage src={shinyPreview} alt="shiny preview" />}
              <PaletteStrip
                colors={result.shiny.colors}
                usedIndices={result.shiny.colors.map((_,i) => i)}
                checkSize="100%"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab root
// ---------------------------------------------------------------------------
export function ShinyTab() {
  const [mode, setMode] = useState('apply')   // 'apply' | 'extract'
  const [palettes, setPalettes] = useState([])

  useEffect(() => {
    fetch(`${API}/palettes`).then(r => r.json()).then(setPalettes).catch(() => {})
  }, [])

  return (
    <div className="tab-content">
      <div style={{ marginBottom: 20 }}>
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === 'apply' ? 'active' : ''}`}
            onClick={() => setMode('apply')}
          >
            apply shiny palette
            <div style={{ fontSize: 9, opacity: 0.8, marginTop: 2 }}>
              sprite + normal pal + shiny pal → preview
            </div>
          </button>
          <button
            className={`mode-btn ${mode === 'extract' ? 'active' : ''}`}
            onClick={() => setMode('extract')}
          >
            extract matched palettes
            <div style={{ fontSize: 9, opacity: 0.8, marginTop: 2 }}>
              normal sprite + shiny sprite → two index-matched .pal files
            </div>
          </button>
        </div>
      </div>

      {mode === 'apply'   && <ApplyShinyMode palettes={palettes} />}
      {mode === 'extract' && <ExtractMatchedMode />}
    </div>
  )
}