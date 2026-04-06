import { useState, useEffect, useRef } from 'react'
import './ExtractTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { BgColorPicker } from '../components/BgColorPicker'
import { useFetch } from '../hooks/useFetch'
import { Info, Download, Save, Check, X, Palette, RefreshCw } from 'lucide-react'
import { ColorSwatch } from '../components/ColorSwatch'
import { Modal } from '../components/Modal'
import { detectBgColor, downloadBlob } from '../utils'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'
const MAX_EXTRA_COLORS = 15
const CS_KEY = 'porypal_extract_cs'

// ---------------------------------------------------------------------------
// Help modal
// ---------------------------------------------------------------------------
function HelpModal({ onClose }) {
  return (
    <Modal title="palette extraction" onClose={onClose}>
      <p className="modal-desc">
        Extracts a GBA-compatible 16-color palette from any sprite using k-means clustering.
        Both color spaces are shown so you can pick the best result.
      </p>
      <div className="help-steps">
        <div className="help-step">
          <span className="help-step-num">1</span>
          <div>
            <strong>Drop a sprite</strong>
            <p>Palette extraction runs automatically. Tweak settings and hit re-extract if needed.</p>
          </div>
        </div>
        <div className="help-step">
          <span className="help-step-num">2</span>
          <div>
            <strong>Set the transparent color (slot 0)</strong>
            <p>
              <strong>auto</strong> samples the 4 corners · <strong>default</strong> uses
              <code> <ColorSwatch hex="#73C5A4" />#73C5A4</code> (GBA standard) ·
              <strong> custom</strong> lets you type any hex · <strong>pipette</strong> click any pixel.
            </p>
          </div>
        </div>
        <div className="help-step">
          <span className="help-step-num">3</span>
          <div>
            <strong>Download ZIP</strong>
            <p>
              Contains <code>&lt;name&gt;.png</code> (4bpp indexed PNG with palette embedded),
              <code> &lt;name&gt;.pal</code> (JASC-PAL), and <code>manifest.json</code>.
              The last strategy you download is remembered.
            </p>
          </div>
        </div>
      </div>
      <div className="help-note">
        <strong>oklab</strong> clusters by perceptual similarity <strong>(recommended)</strong>.<br></br>
        <strong> rgb</strong> clusters by raw channel distance.
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Method badge
// ---------------------------------------------------------------------------
function MethodBadge({ method }) {
  if (!method) return null
  const embedded = method === 'embedded'
  return (
    <span className={`method-badge ${embedded ? 'method-badge--embedded' : 'method-badge--kmeans'}`}>
      {embedded ? '4bpp detected' : 'k-means'}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Remap preview (client-side, for the live preview only)
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
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data
      const palette = paletteHexColors.map(hexToRgb)
      const [tr, tg, tb] = palette[0]
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) {
          data[i]=tr; data[i+1]=tg; data[i+2]=tb; data[i+3]=255; continue
        }
        const r=data[i], g=data[i+1], b=data[i+2]
        if (r===tr && g===tg && b===tb) continue
        let bestIdx=1, bestDist=Infinity
        for (let j=1; j<palette.length; j++) {
          const [pr,pg,pb]=palette[j]
          const dist=(r-pr)**2+(g-pg)**2+(b-pb)**2
          if (dist<bestDist) { bestDist=dist; bestIdx=j }
        }
        ;[data[i],data[i+1],data[i+2]]=palette[bestIdx]
      }
      ctx.putImageData(imageData, 0, 0)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

// ---------------------------------------------------------------------------
// Single result section (oklab or rgb)
// ---------------------------------------------------------------------------
function ResultSection({ label, result, preview, outputName, isPreferred, file, bgColor, nColors, colorSpace, onSaved }) {
  const [downloading, setDownloading] = useState(false)
  const [saveState, setSaveState]     = useState('idle')

  // Remember preferred color space when the user downloads
  const handleDownloadZip = async () => {
    if (!file || !result) return
    localStorage.setItem(CS_KEY, colorSpace)
    setDownloading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('n_colors', nColors)
      fd.append('bg_color', bgColor)
      fd.append('color_space', colorSpace)
      fd.append('name', outputName)
      const res = await fetch(`${API}/extract/download-zip`, { method: 'POST', body: fd })
      if (!res.ok) return
      downloadBlob(await res.blob(), `${outputName}.zip`)
    } finally { setDownloading(false) }
  }

  const handleSave = async () => {
    if (!result || saveState !== 'idle') return
    setSaveState('saving')
    try {
      const fd = new FormData()
      fd.append('name', outputName)
      fd.append('pal_content', result.pal_content)
      const res = await fetch(`${API}/extract/save`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error()
      setSaveState('saved')
      onSaved?.()
      setTimeout(() => setSaveState('idle'), 2000)
    } catch {
      setSaveState('error')
      setTimeout(() => setSaveState('idle'), 2000)
    }
  }

  if (!preview || !result) return null

  return (
    <div className={`extract-preview-section ${isPreferred ? 'extract-preview-preferred' : ''}`}>
      <div className="extract-section-header">
        <p className="section-label">
          {label}
          {isPreferred && <span className="extract-preferred-dot" title="last used strategy" />}
        </p>
        <MethodBadge method={result.method} />
      </div>

      <ZoomableImage src={preview} alt={label} />

      <div className="palette-strip-wrap">
        <PaletteStrip colors={result.colors} usedIndices={result.colors.map((_, i) => i)} />
      </div>

      {/* Primary: Download ZIP */}
      <button
        className="btn-primary extract-download-btn"
        onClick={handleDownloadZip}
        disabled={downloading}
      >
        <Download size={13} />
        {downloading ? 'downloading…' : `Download '${outputName}.zip'`}
      </button>

      {/* Secondary: Save to library */}
      <button
        className={`btn-secondary extract-save-btn ${saveState === 'saved' ? 'extract-save-btn--saved' : saveState === 'error' ? 'extract-save-btn--error' : ''}`}
        onClick={handleSave}
        disabled={saveState !== 'idle'}
      >
        {saveState === 'saved'  ? <><Check size={11}/> saved to library</>
       : saveState === 'error' ? <><X size={11}/> failed</>
       : <><Save size={11}/> Save palette to library</>}
      </button>
    </div>
  )
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
  const [outputName, setOutputName]   = useState('')

  // Persisted color space preference
  const [preferredCs] = useState(() => localStorage.getItem(CS_KEY) || 'oklab')

  const [resultOklab, setResultOklab]   = useState(null)
  const [resultRgb, setResultRgb]       = useState(null)
  const [previewOklab, setPreviewOklab] = useState(null)
  const [previewRgb, setPreviewRgb]     = useState(null)

  const [picking, setPicking]   = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  const { loading, error, run } = useFetch()
  const bgColorRef = useRef(bgColor)
  bgColorRef.current = bgColor

  // Image dimensions
  useEffect(() => {
    if (!originalB64) return
    const img = new window.Image()
    img.onload = () => setImageSize({ w: img.naturalWidth, h: img.naturalHeight })
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  // Previews
  useEffect(() => {
    if (!originalB64 || !resultOklab?.colors?.length) { setPreviewOklab(null); return }
    remapToPalette(originalB64, resultOklab.colors).then(setPreviewOklab)
  }, [resultOklab, originalB64])

  useEffect(() => {
    if (!originalB64 || !resultRgb?.colors?.length) { setPreviewRgb(null); return }
    remapToPalette(originalB64, resultRgb.colors).then(setPreviewRgb)
  }, [resultRgb, originalB64])

  // ---------------------------------------------------------------------------

  const runExtract = (f, bg) => {
    const doOne = async (cs) => {
      const fd = new FormData()
      fd.append('file', f)
      fd.append('n_colors', nColors)
      fd.append('bg_color', bg)
      fd.append('color_space', cs)
      const res = await fetch(`${API}/extract`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    }
    run(async () => {
      const [oklab, rgb] = await Promise.all([doOne('oklab'), doOne('rgb')])
      setResultOklab(oklab)
      setResultRgb(rgb)
    })
  }

  const handleFile = (f) => {
    setFile(f)
    setResultOklab(null); setResultRgb(null)
    setPreviewOklab(null); setPreviewRgb(null)
    setOutputName(f.name.replace(/\.[^.]+$/, ''))

    const reader = new FileReader()
    reader.onload = e => {
      const b64 = e.target.result.split(',')[1]
      setOriginalB64(b64)
      detectBgColor(b64).then(detected => {
        setBgColor(detected); setBgMode('auto')
        runExtract(f, detected)   // ← auto-extract on drop
      })
    }
    reader.readAsDataURL(f)
  }

  const handlePick = (hex) => {
    setBgColor(hex); setBgMode('pick'); setPicking(false)
  }

  const tooMany   = nColors > MAX_EXTRA_COLORS
  const isEmbedded = resultOklab?.method === 'embedded'

  // Preferred result shows first
  const firstCs  = preferredCs === 'rgb' ? 'rgb'   : 'oklab'
  const secondCs = preferredCs === 'rgb' ? 'oklab' : 'rgb'

  const resultMap  = { oklab: resultOklab,  rgb: resultRgb  }
  const previewMap = { oklab: previewOklab, rgb: previewRgb }

  return (
    <div className="tab-content">
      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}

      <div className="extract-layout">

        {/* ── Left ── */}
        <div className="extract-left">
          <DropZone onFile={handleFile} label="Drop sprite to extract palette" />

          {/* Output name — only shown once a file is loaded */}
          {file && (
            <div className="field">
              <label className="field-label">output name</label>
              <input
                className="field-input"
                value={outputName}
                onChange={e => setOutputName(e.target.value)}
                spellCheck={false}
                placeholder="sprite_name"
              />
              <span className="field-hint">used for .zip, .png and .pal filenames</span>
            </div>
          )}

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
                GBA supports max 16 colors — slot 0 is reserved for transparent
              </p>
            )}
          </div>

          <div className="field">
            <label className="field-label">transparent color (slot 0)</label>
            <BgColorPicker
              color={bgColor}
              mode={bgMode}
              onChange={({ color, mode }) => { setBgColor(color); setBgMode(mode) }}
              showAuto={!!originalB64}
              onAutoDetect={() => detectBgColor(originalB64)}
              showPipette={!!originalB64}
              picking={picking}
              onPipetteToggle={() => setPicking(p => !p)}
            />
          </div>

          <button
            className="btn-primary"
            disabled={!file || loading || tooMany}
            onClick={() => runExtract(file, bgColor)}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
          >
            <RefreshCw size={13} className={loading ? 'spinning' : ''} />
            {loading ? 'extracting…' : resultOklab ? 're-extract' : 'extract palette'}
          </button>

          {error && <p className="error-msg">{error}</p>}
        </div>

        {/* ── Right ── */}
        <div className="extract-right">
          <div className="extract-toolbar">
            <span className="section-label">
              {resultOklab
                ? `${outputName} — ${resultOklab.colors.length} colors`
                : 'preview'
              }
            </span>
            <button className="help-btn" onClick={() => setShowHelp(true)} title="Help">
              <Info size={15}/>
            </button>
          </div>

          {!originalB64 && (
            <div className="empty-state">drop a sprite to extract a GBA-compatible palette</div>
          )}

          {originalB64 && (
            <div className="extract-previews">

              {/* Original */}
              <div className="extract-preview-section">
                <p className="section-label">
                  original{imageSize ? ` — ${imageSize.w}×${imageSize.h}px` : ''}
                  {picking && <span className="pick-hint"> · click to pick bg color</span>}
                </p>
                <ZoomableImage
                  src={originalB64} alt="source sprite"
                  picking={picking} onPick={handlePick}
                />
              </div>

              {/* Embedded: single result */}
              {isEmbedded && (
                <ResultSection
                  label="result"
                  result={resultOklab}
                  preview={previewOklab}
                  outputName={outputName}
                  isPreferred
                  file={file} bgColor={bgColor} nColors={nColors} colorSpace="oklab"
                />
              )}

              {/* K-means: preferred first, other second */}
              {!isEmbedded && (
                <>
                  <ResultSection
                    label={`${firstCs}${firstCs === 'oklab' ? ' — recommended' : ''}`}
                    result={resultMap[firstCs]}
                    preview={previewMap[firstCs]}
                    outputName={outputName}
                    isPreferred={preferredCs === firstCs}
                    file={file} bgColor={bgColor} nColors={nColors} colorSpace={firstCs}
                  />
                  <ResultSection
                    label={secondCs}
                    result={resultMap[secondCs]}
                    preview={previewMap[secondCs]}
                    outputName={outputName}
                    isPreferred={preferredCs === secondCs}
                    file={file} bgColor={bgColor} nColors={nColors} colorSpace={secondCs}
                  />
                </>
              )}

            </div>
          )}
        </div>

      </div>
    </div>
  )
}