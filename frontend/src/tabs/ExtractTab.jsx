import { useState, useEffect } from 'react'
import './ExtractTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { useFetch } from '../hooks/useFetch'
import { Info, Pipette, PaintBucket, X, Eclipse, Palette, Scan } from 'lucide-react'
import { ColorSwatch } from '../components/ColorSwatch'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'
const MAX_COLORS = 16
const MAX_EXTRA_COLORS = MAX_COLORS - 1

// ---------------------------------------------------------------------------
// Corner-based background color detection
// Samples the 4 corners, returns the majority color.
// Falls back to top-left if all 4 differ.
// ---------------------------------------------------------------------------
function detectBgColor(imageB64) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const w = canvas.width - 1
      const h = canvas.height - 1
      const corners = [
        ctx.getImageData(0, 0, 1, 1).data,
        ctx.getImageData(w, 0, 1, 1).data,
        ctx.getImageData(0, h, 1, 1).data,
        ctx.getImageData(w, h, 1, 1).data,
      ].map(d => {
        if (d[3] < 128) return null  // skip transparent corners
        return `#${d[0].toString(16).padStart(2,'0')}${d[1].toString(16).padStart(2,'0')}${d[2].toString(16).padStart(2,'0')}`
      })
      const counts = {}
      for (const c of corners) {
        if (c) counts[c] = (counts[c] || 0) + 1
      }
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])
      resolve(sorted.length > 0 ? sorted[0][0] : GBA_TRANSPARENT)
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

// ---------------------------------------------------------------------------
// Help modal
// ---------------------------------------------------------------------------
function HelpModal({ onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">palette extraction</span>
          <button className="modal-close" onClick={onClose}><X size={16}/></button>
        </div>
        <div className="modal-body">
          <p className="modal-desc">
            Extracts a GBA-compatible 16-color palette from any sprite using k-means clustering.
            Both color spaces are shown so you can pick the best result.
          </p>
          <div className="help-steps">
            <div className="help-step">
              <span className="help-step-num">1</span>
              <div>
                <strong>Drop a sprite</strong>
                <p>Any PNG or image with the colors you want to extract.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">2</span>
              <div>
                <strong>Set the transparent color (slot 0)</strong>
                <p>This color will always be first in the palette. The GBA uses slot 0 as the background/transparent color.</p>
                <ul className="help-list">
                  <li><span className="help-tag">auto <Scan size={8} /></span> samples the 4 corners and picks the majority color — works for most sprites</li>
                  <li><span className="help-tag">default <Eclipse size={8} /></span> uses <code><ColorSwatch hex="#73C5A4" />#73C5A4</code>, the standard GBA transparent green</li>
                  <li><span className="help-tag">custom <PaintBucket size={8} /></span> lets you type any hex value</li>
                  <li><span className="help-tag">pipette <Pipette size={8} /></span> click any pixel on your sprite to sample it directly</li>
                </ul>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">3</span>
              <div>
                <strong>Choose color count</strong>
                <p>Max 15 sprite colors + 1 transparent = 16 total. GBA palettes are hard-limited to 16 colors per palette bank.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">4</span>
              <div>
                <strong>Compare & Download</strong>
                <p>
                  <strong>Oklab:</strong> Clusters by perceptual similarity. <b>RECOMMENDED.</b>{' '}
                  <strong>RGB:</strong> Clusters by raw channel distance. (Less faithful to original colors.)
                </p>
              </div>
            </div>
          </div>
          <div className="help-note">
            <strong>JASC-PAL format</strong> — compatible with Porypal, Usenti, and most GBA sprite editors.
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Remap preview
// ---------------------------------------------------------------------------
function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)]
}

function remapToPalette(imageB64, paletteHexColors) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data
      const palette = paletteHexColors.map(hexToRgb)
      const [tr, tg, tb] = palette[0]
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) {
          data[i] = tr; data[i+1] = tg; data[i+2] = tb; data[i+3] = 255
          continue
        }
        const r = data[i], g = data[i+1], b = data[i+2]
        let bestIdx = 0, bestDist = Infinity
        for (let j = 0; j < palette.length; j++) {
          const [pr,pg,pb] = palette[j]
          const dist = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
          if (dist < bestDist) { bestDist = dist; bestIdx = j }
        }
        ;[data[i], data[i+1], data[i+2]] = palette[bestIdx]
      }
      ctx.putImageData(imageData, 0, 0)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

// ---------------------------------------------------------------------------
// Tab
// ---------------------------------------------------------------------------
export function ExtractTab() {
  const [file, setFile]               = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [nColors, setNColors]         = useState(15)
  const [bgColor, setBgColor]         = useState(GBA_TRANSPARENT)
  const [bgMode, setBgMode]           = useState('default')
  const [imageSize, setImageSize]     = useState(null)

  const [resultOklab, setResultOklab]   = useState(null)
  const [resultRgb, setResultRgb]       = useState(null)
  const [previewOklab, setPreviewOklab] = useState(null)
  const [previewRgb, setPreviewRgb]     = useState(null)

  const [picking, setPicking]   = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  const { loading, error, run } = useFetch()

  useEffect(() => {
    if (!originalB64) return
    const img = new window.Image()
    img.onload = () => setImageSize({ w: img.naturalWidth, h: img.naturalHeight })
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  useEffect(() => {
    if (!originalB64) return
    if (resultOklab?.colors?.length > 1)
      remapToPalette(originalB64, resultOklab.colors).then(setPreviewOklab)
    else
      setPreviewOklab(null)
    if (resultRgb?.colors?.length > 1)
      remapToPalette(originalB64, resultRgb.colors).then(setPreviewRgb)
    else
      setPreviewRgb(null)
  }, [resultOklab, resultRgb, originalB64])

  const handleFile = (f) => {
    setFile(f)
    setResultOklab(null); setResultRgb(null)
    setPreviewOklab(null); setPreviewRgb(null)
    const reader = new FileReader()
    reader.onload = e => {
      const b64 = e.target.result.split(',')[1]
      setOriginalB64(b64)
      // Auto-detect bg color from corners on every new file
      detectBgColor(b64).then(detected => {
        setBgColor(detected)
        setBgMode('auto')
      })
    }
    reader.readAsDataURL(f)
  }

  const runExtract = async (space) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('n_colors', nColors)
    fd.append('bg_color', bgColor)
    fd.append('color_space', space)
    const res = await fetch(`${API}/extract`, { method: 'POST', body: fd })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }

  const handleExtract = () => {
    if (!file) return
    run(async () => {
      const [oklab, rgb] = await Promise.all([runExtract('oklab'), runExtract('rgb')])
      setResultOklab(oklab)
      setResultRgb(rgb)
    })
  }

  const downloadPal = (result) => {
    const blob = new Blob([result.pal_content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${result.name}_${result.color_space}.pal`
    a.click()
  }

  const handlePick = (hex) => {
    setBgColor(hex)
    setBgMode('pick')
    setPicking(false)
  }

  const tooMany = nColors > MAX_EXTRA_COLORS

  return (
    <div className="tab-content">
      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}

      <div className="extract-layout">

        {/* ── Left: controls ── */}
        <div className="extract-left">
          <DropZone onFile={handleFile} label="Drop sprite to extract palette" />

          <div className="field">
            <label className="field-label">colors (max 15 + transparent = 16 for GBA)</label>
            <input
              type="number"
              className={`field-input ${tooMany ? 'field-error' : ''}`}
              min={1} max={MAX_EXTRA_COLORS}
              value={nColors}
              onChange={e => setNColors(Number(e.target.value))}
            />
            {tooMany && (
              <p className="field-hint-error">
                GBA supports max 16 colors — slot 0 is reserved for transparent, leaving 15 for sprite colors
              </p>
            )}
          </div>

          <div className="field">
            <label className="field-label">transparent color (slot 0)</label>
            <div className="bg-mode-row">
              {originalB64 && (
                <button
                  className={`bg-mode-btn ${bgMode === 'auto' ? 'active' : ''}`}
                  onClick={() =>
                    detectBgColor(originalB64).then(detected => {
                      setBgColor(detected); setBgMode('auto')
                    })
                  }
                  title="detect from image corners"
                >auto <Scan size={8} /></button>
              )}
              <button
                className={`bg-mode-btn ${bgMode === 'default' ? 'active' : ''}`}
                onClick={() => { setBgMode('default'); setBgColor(GBA_TRANSPARENT) }}
              >default <Eclipse size={8} /></button>
              <button
                className={`bg-mode-btn ${bgMode === 'custom' ? 'active' : ''}`}
                onClick={() => setBgMode('custom')}
              >custom <PaintBucket size={8} /></button>
              {originalB64 && (
                <button
                  className={`bg-mode-btn ${picking ? 'picking' : ''}`}
                  onClick={() => setPicking(p => !p)}
                  title="click a pixel on the image to pick its color"
                >pipette <Pipette size={8} /></button>
              )}
            </div>

            <div className="bg-color-row">
              <div className="bg-swatch" style={{ background: bgColor }} />
              {bgMode === 'custom' || bgMode === 'pick' ? (
                <input
                  className="field-input field-mono"
                  value={bgColor}
                  onChange={e => setBgColor(e.target.value)}
                  placeholder="#73C5A4"
                  maxLength={7}
                />
              ) : (
                <span className="field-hint">
                  {bgColor}
                  {bgMode === 'auto'    && <span className="bg-mode-tag"> auto-detected</span>}
                  {bgMode === 'default' && <span className="bg-mode-tag"> GBA default</span>}
                </span>
              )}
            </div>
          </div>

          <div className="extract-actions">
            <button
              className="btn-primary"
              disabled={!file || loading || tooMany}
              onClick={handleExtract}
            >
              {loading ? 'extracting… ' : 'extract palette '}
              <Palette size={10} />
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}
        </div>

        {/* ── Right: stacked previews ── */}
        <div className="extract-right">

          <div className="extract-toolbar">
            <span className="section-label">
              {resultOklab
                ? `${resultOklab.name} — ${resultOklab.colors.length} colors`
                : 'preview'}
            </span>
            <button className="help-btn" onClick={() => setShowHelp(true)} title="Help">
              <Info size={15}/>
            </button>
          </div>

          {!originalB64 && (
            <div className="empty-state">
              drop a sprite to extract a GBA-compatible palette
            </div>
          )}

          {originalB64 && (
            <div className="extract-previews">

              <div className="extract-preview-section">
                <p className="section-label">
                  original{imageSize ? ` — ${imageSize.w}×${imageSize.h}px` : ''}
                  {picking && <span className="pick-hint"> · click to pick bg color</span>}
                </p>
                <ZoomableImage
                  src={originalB64}
                  alt="source sprite"
                  picking={picking}
                  onPick={handlePick}
                />
              </div>

              {previewOklab && resultOklab && (
                <div className="extract-preview-section">
                  <div className="extract-section-header">
                    <p className="section-label">oklab — recommended</p>
                    <button className="btn-dl" onClick={() => downloadPal(resultOklab)}>↓ .pal</button>
                  </div>
                  <ZoomableImage src={previewOklab} alt="oklab preview" />
                  <div className="palette-strip-wrap">
                    <PaletteStrip
                      colors={resultOklab.colors}
                      usedIndices={resultOklab.colors.map((_, i) => i)}
                    />
                  </div>
                </div>
              )}

              {previewRgb && resultRgb && (
                <div className="extract-preview-section">
                  <div className="extract-section-header">
                    <p className="section-label">rgb</p>
                    <button className="btn-dl" onClick={() => downloadPal(resultRgb)}>↓ .pal</button>
                  </div>
                  <ZoomableImage src={previewRgb} alt="rgb preview" />
                  <div className="palette-strip-wrap">
                    <PaletteStrip
                      colors={resultRgb.colors}
                      usedIndices={resultRgb.colors.map((_, i) => i)}
                    />
                  </div>
                </div>
              )}

            </div>
          )}

        </div>

      </div>
    </div>
  )
}