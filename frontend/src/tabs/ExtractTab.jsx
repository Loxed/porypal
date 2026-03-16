import { useState, useEffect } from 'react'
import './ExtractTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { useFetch } from '../hooks/useFetch'
import { Info, X } from 'lucide-react'
import { ColorSwatch } from '../components/ColorSwatch'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'
const MAX_COLORS = 16
const MAX_EXTRA_COLORS = MAX_COLORS - 1

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
          </p>

          <div className="help-steps">
            <div className="help-step">
              <span className="help-step-num">1</span>
              <div>
                <strong>drop a sprite</strong>
                <p>Any PNG or image with the colors you want to extract.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">2</span>
              <div>
                <strong>set the transparent color (slot 0)</strong>
                <p>This color will always be first in the palette. The GBA uses slot 0 as the background/transparent color.</p>
                <ul className="help-list">
                  <li><span className="help-tag">default</span> uses <code><ColorSwatch hex="#73C5A4" />#73C5A4</code>, the standard GBA transparent green</li>
                  <li><span className="help-tag">custom</span> lets you type any hex value</li>
                  <li><span className="help-tag">pipette</span> click any pixel on your sprite to sample it directly</li>
                </ul>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">3</span>
              <div>
                <strong>choose color count</strong>
                <p>Max 15 sprite colors + 1 transparent = 16 total. GBA palettes are hard-limited to 16 colors per palette bank.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">4</span>
              <div>
                <strong>extract & download</strong>
                <p>The <em>palette applied</em> preview shows how your sprite will look remapped to the extracted palette. Download the <code>.pal</code> file to load it into Porypal or any JASC-PAL compatible tool.</p>
              </div>
            </div>
          </div>

          <div className="help-note">
            <strong>JASC-PAL format</strong> — the output is compatible with Porypal, Usenti, and most GBA sprite editors.
          </div>
        </div>
      </div>
    </div>
  )
}

function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
}

function remapToPalette(imageB64, paletteHexColors) {
  return new Promise((resolve) => {
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
        if (data[i + 3] < 128) {
          data[i] = tr; data[i + 1] = tg; data[i + 2] = tb; data[i + 3] = 255
          continue
        }
        const r = data[i], g = data[i + 1], b = data[i + 2]
        let bestIdx = 1, bestDist = Infinity
        for (let j = 1; j < palette.length; j++) {
          const [pr, pg, pb] = palette[j]
          const dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
          if (dist < bestDist) { bestDist = dist; bestIdx = j }
        }
        ;[data[i], data[i + 1], data[i + 2]] = palette[bestIdx]
      }
      ctx.putImageData(imageData, 0, 0)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

export function ExtractTab() {
  const [file, setFile] = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [nColors, setNColors] = useState(15)
  const [bgColor, setBgColor] = useState(GBA_TRANSPARENT)
  const [bgMode, setBgMode] = useState('default')
  const [result, setResult] = useState(null)
  const [previewB64, setPreviewB64] = useState(null)
  const [picking, setPicking] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [imageSize, setImageSize] = useState(null)
  const { loading, error, run } = useFetch()

  useEffect(() => {
    if (!originalB64) return
    const img = new window.Image()
    img.onload = () => setImageSize({ w: img.naturalWidth, h: img.naturalHeight })
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  useEffect(() => {
    if (!result || !originalB64 || result.colors.length < 2) { setPreviewB64(null); return }
    remapToPalette(originalB64, result.colors).then(setPreviewB64)
  }, [result, originalB64])

  const handleFile = (f) => {
    setFile(f); setResult(null); setPreviewB64(null)
    const reader = new FileReader()
    reader.onload = e => setOriginalB64(e.target.result.split(',')[1])
    reader.readAsDataURL(f)
  }

  const handleExtract = async () => {
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('n_colors', nColors)
    fd.append('bg_color', bgColor)
    const data = await run(async () => {
      const res = await fetch(`${API}/extract`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) setResult(data)
  }

  const handlePick = (hex) => {
    setBgColor(hex)
    setBgMode('pick')
    setPicking(false)
  }

  const handleDownloadPal = () => {
    const blob = new Blob([result.pal_content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${result.name}.pal`
    a.click()
  }

  const colorCount = result?.colors?.length ?? 0
  const tooMany = nColors > MAX_EXTRA_COLORS

  return (
    <div className="tab-content">
      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}
      <div className="extract-layout">

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
                GBA supports max 16 colors total — slot 0 is reserved for transparent, leaving 15 for sprite colors
              </p>
            )}
          </div>

          <div className="field">
            <label className="field-label">transparent color (slot 0)</label>
            <div className="bg-mode-row">
              <button
                className={`bg-mode-btn ${bgMode === 'default' ? 'active' : ''}`}
                onClick={() => { setBgMode('default'); setBgColor(GBA_TRANSPARENT) }}
              >default</button>
              <button
                className={`bg-mode-btn ${bgMode === 'custom' ? 'active' : ''}`}
                onClick={() => setBgMode('custom')}
              >custom</button>
              {originalB64 && (
                <button
                  className={`bg-mode-btn ${picking ? 'picking' : ''}`}
                  onClick={() => setPicking(p => !p)}
                  title="click a pixel on the image to pick its color"
                >pipette</button>
              )}
            </div>
            {(bgMode === 'custom' || bgMode === 'pick') && (
              <div className="bg-color-row">
                <div className="bg-swatch" style={{ background: bgColor }} />
                <input
                  className="field-input field-mono"
                  value={bgColor}
                  onChange={e => setBgColor(e.target.value)}
                  placeholder="#73C5A4"
                  maxLength={7}
                />
              </div>
            )}
            {bgMode === 'default' && (
              <div className="bg-color-row">
                <div className="bg-swatch" style={{ background: GBA_TRANSPARENT }} />
                <span className="field-hint">{GBA_TRANSPARENT} (GBA default)</span>
              </div>
            )}
          </div>

          <div className="extract-actions">
            <button
              className="btn-primary"
              disabled={!file || loading || tooMany}
              onClick={handleExtract}
            >
              {loading ? 'extracting…' : 'extract palette'}
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}
        </div>

        <div className="extract-right">
          <div className="extract-toolbar">
            <span className="section-label">
              {result ? `${result.name} — ${colorCount} colors` : 'preview'}
            </span>
            <button className="help-btn" onClick={() => setShowHelp(true)}><Info size={15}/></button>
          </div>
          {!originalB64 && !result && (
            <div className="empty-state">
              <p>drop a sprite to extract a GBA-compatible palette</p>
            </div>
          )}

          {originalB64 && (
            <div className="extract-previews">
              <div className="extract-preview-section">
                <p className="section-label">
                  original{imageSize ? ` — ${imageSize.w}×${imageSize.h}px` : ''}
                  {picking && <span className="pick-hint"> · click to pick bg color</span>}
                </p>
                <div className="extract-image-wrap">
                  <ZoomableImage
                    src={originalB64}
                    alt="source sprite"
                    picking={picking}
                    onPick={handlePick}
                  />
                </div>
              </div>

              {previewB64 && (
                <div className="extract-preview-section">
                  <p className="section-label">palette applied</p>
                  <div className="extract-image-wrap">
                    <ZoomableImage src={previewB64} alt="palette preview" />
                  </div>
                </div>
              )}
            </div>
          )}

          {result && (
            <div className="extract-result-section">
              <div className="extract-result-header">
                <button className="btn-primary-sm" onClick={handleDownloadPal}>download .pal</button>
              </div>
              <div className="palette-strip-wrap">
                <PaletteStrip
                  colors={result.colors}
                  usedIndices={result.colors.map((_, i) => i)}
                />
                <span className="transparent-label">transp.</span>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}