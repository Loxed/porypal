import { useState, useRef } from 'react'
import { Download, X, Star } from 'lucide-react'
import { ZoomableImage } from './ZoomableImage'
import { PaletteStrip } from './PaletteStrip'
import { BgColorCell } from './BgColorCell'
import { BgColorPicker } from './BgColorPicker'
import { detectBgColor, downloadBlob } from '../utils'
import './VariantsPanel.css'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

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

export function VariantsPanel({ nColors, outputBg, outputBgMode, setOutputBg, setOutputBgMode }) {
  const [sprites, setSprites]       = useState([])
  const [refIndex, setRefIndex]     = useState(0)
  const [results, setResults]       = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [viewMode, setViewMode]     = useState('grid')
  const inputRef = useRef()

  const handleFiles = async (fileList) => {
    const sorted = Array.from(fileList).sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
    )
    const loaded = await Promise.all(sorted.map(async f => {
      const b64     = await fileToB64(f)
      const inputBg = await detectBgColor(b64)
      return { file: f, name: f.name.replace(/\.[^.]+$/, ''), b64, inputBg }
    }))
    setSprites(prev => {
      const names  = new Set(prev.map(s => s.name))
      const merged = [...prev, ...loaded.filter(s => !names.has(s.name))]
      return merged.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
    })
    setResults(null)
  }

  const updateInputBg = (idx, color) =>
    setSprites(prev => prev.map((s, i) => i === idx ? { ...s, inputBg: color } : s))

  const removeSprite = (idx) => {
    setSprites(prev => prev.filter((_, i) => i !== idx))
    if (refIndex >= idx && refIndex > 0) setRefIndex(r => r - 1)
    setResults(null)
  }

  const handleExtract = async () => {
    if (sprites.length < 1) return
    setLoading(true); setError(null); setResults(null)
    try {
      const fd = new FormData()
      sprites.forEach(s => fd.append('files', s.file))
      fd.append('n_colors', nColors)
      fd.append('input_bg_colors', JSON.stringify(sprites.map(s => s.inputBg)))
      fd.append('output_bg_color', outputBg)
      fd.append('reference_index', refIndex)
      const res = await fetch(`${API}/items/extract-variants`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      setResults(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadAll = async () => {
    const fd = new FormData()
    sprites.forEach(s => fd.append('files', s.file))
    fd.append('n_colors', nColors)
    fd.append('input_bg_colors', JSON.stringify(sprites.map(s => s.inputBg)))
    fd.append('output_bg_color', outputBg)
    fd.append('reference_index', refIndex)
    const res = await fetch(`${API}/items/extract-variants/download`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), 'variant_palettes.zip')
  }

  return (
    <div className="variants-layout">

      {/* ── Left ── */}
      <div className="variants-left">

        <div
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files) }}
        >
          <div className="dropzone" onClick={() => inputRef.current?.click()}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--muted)' }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p className="dropzone-label">Drop variant sprites</p>
            <p className="dropzone-hint">same size · different hues · sorted A–Z</p>
          </div>
          <input ref={inputRef} type="file" accept="image/*" multiple style={{ display: 'none' }}
            onChange={e => { if (e.target.files.length) handleFiles(e.target.files); e.target.value = '' }} />
        </div>

        {sprites.length > 0 && (
          <div className="variants-sprite-queue">
            {sprites.map((s, i) => (
              <div key={s.name} className={`variants-queue-row ${i === refIndex ? 'is-ref' : ''}`}>
                <img src={`data:image/png;base64,${s.b64}`} alt={s.name} className="sprite-queue-thumb" />
                <span className="sprite-queue-name">{s.name}</span>
                <BgColorCell color={s.inputBg} onChange={color => updateInputBg(i, color)} />
                <button
                  className={`ref-star-btn ${i === refIndex ? 'active' : ''}`}
                  title={i === refIndex ? 'reference sprite (sets slot order)' : 'set as reference'}
                  onClick={() => { setRefIndex(i); setResults(null) }}
                >
                  <Star size={10} fill={i === refIndex ? 'currentColor' : 'none'} />
                </button>
                <button className="sprite-queue-btn danger" title="remove" onClick={() => removeSprite(i)}>
                  <X size={10} />
                </button>
              </div>
            ))}
            <p className="variants-ref-hint">
              ★ = reference — sets the palette slot order for all variants
            </p>
          </div>
        )}

        <div className="field">
          <label className="field-label">output transparent (slot 0)</label>
          <BgColorPicker
            color={outputBg}
            mode={outputBgMode}
            onChange={({ color, mode }) => { setOutputBg(color); setOutputBgMode(mode) }}
          />
        </div>

        <button className="btn-primary" disabled={sprites.length < 1 || loading} onClick={handleExtract}>
          {loading ? 'extracting…' : `extract ${sprites.length} variant${sprites.length !== 1 ? 's' : ''}`}
        </button>

        {results && (
          <button className="btn-secondary" onClick={handleDownloadAll}>
            <Download size={11} /> download all as zip
          </button>
        )}

        {error && <p className="error-msg">{error}</p>}

        <div className="variants-explainer">
          <p className="section-label">how it works</p>
          <p>Drop N sprites that are hue-shifted versions of the same base (e.g. potion + super potion).</p>
          <p>Mark one as the ★ reference — it sets the slot order. Every other variant gets a palette where each slot maps to the color at the same pixel positions in that sprite.</p>
          <p>Result: all palettes are index-compatible. Use the same sprite with any of the extracted palettes in-game.</p>
        </div>
      </div>

      {/* ── Right ── */}
      <div className="variants-right">
        <div className="items-toolbar">
          <span className="items-count">
            {results ? `${results.results.length} variant${results.results.length !== 1 ? 's' : ''} · ref: ${results.reference}` : ''}
          </span>
          {results && (
            <div className="view-toggle">
              <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              </button>
              <button className={`view-btn ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="4" width="18" height="2"/><rect x="3" y="11" width="18" height="2"/><rect x="3" y="18" width="18" height="2"/></svg>
              </button>
            </div>
          )}
        </div>

        {!results && !loading && (
          <div className="empty-state">
            <p>drop recolor variants to extract index-compatible palettes</p>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              potion.png + super_potion.png → potion.pal + super_potion.pal with matching slots
            </p>
          </div>
        )}
        {loading && <div className="empty-state"><div className="spinner" /><p>matching palettes…</p></div>}

        {results && (
          <div className={viewMode === 'grid' ? 'variants-results-grid' : 'variants-results-list'}>
            {results.results.map((r) => (
              <div key={r.name} className={`variant-card ${r.name === results.reference ? 'is-reference' : ''} ${viewMode === 'list' ? 'list-mode' : ''}`}>
                {viewMode === 'list' ? (
                  <>
                    <div className="variant-card-preview">
                      <ZoomableImage src={r.preview} alt={r.name} />
                    </div>
                    <div className="variant-card-body">
                      <div className="variant-card-header">
                        <span className="variant-card-name">{r.name}</span>
                        {r.name === results.reference && <span className="item-card-ref-badge">ref</span>}
                        <button className="sprite-queue-btn" onClick={() => downloadPal(r.pal_content, r.name)}>
                          <Download size={11} />
                        </button>
                      </div>
                      <PaletteStrip colors={r.colors} usedIndices={r.colors.map((_, i) => i)} checkSize="50%" />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="variant-card-header">
                      <span className="variant-card-name">{r.name}</span>
                      {r.name === results.reference && <span className="item-card-ref-badge">ref</span>}
                    </div>
                    <PaletteStrip colors={r.colors} usedIndices={r.colors.map((_, i) => i)} checkSize="100%" />
                    <ZoomableImage src={r.preview} alt={r.name} />
                    <button className="btn-secondary" onClick={() => downloadPal(r.pal_content, r.name)}>
                      <Download size={11} /> download .pal
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}