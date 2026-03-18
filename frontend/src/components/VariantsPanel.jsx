import { useState, useRef, useMemo, useEffect } from 'react'
import { Download, X, Upload, AlertTriangle } from 'lucide-react'
import { ZoomableImage } from './ZoomableImage'
import { PaletteStrip } from './PaletteStrip'
import { BgColorCell } from './BgColorCell'
import { BgColorPicker } from './BgColorPicker'
import { ViewToggle } from './ViewToggle'
import { detectBgColor, downloadBlob, remapToShinyPalette } from '../utils'
import './VariantsPanel.css'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

// Fraction of ref slots that are empty in a variant before we warn
const SLOT_WARN_THRESHOLD  = 0.15   // yellow
const SLOT_ERROR_THRESHOLD = 0.35   // red

function fileToB64(file) {
  return new Promise(resolve => {
    const reader = new FileReader()
    reader.onload = e => resolve(e.target.result.split(',')[1])
    reader.readAsDataURL(file)
  })
}

function getImageDimensions(b64) {
  return new Promise(resolve => {
    const img = new Image()
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight })
    img.src = `data:image/png;base64,${b64}`
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

function downloadPal(palContent, filename) {
  const blob = new Blob([palContent], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename.endsWith('.pal') ? filename : `${filename}.pal`
  a.click()
}

// ---------------------------------------------------------------------------
// Slot-based mismatch: compare variant palette slots against reference.
// A slot is "empty" in the variant if its color equals the output bg —
// meaning no pixels from that variant mapped to that slot position.
// Returns { emptySlots, totalRefSlots, score } where score is 0–1.
// ---------------------------------------------------------------------------
function computeSlotMatch(refColors, variantColors, outputBg) {
  const bg = outputBg.toLowerCase()
  // Count non-bg slots in the reference (slots 1+, skip slot 0 which is always bg)
  let totalRefSlots = 0
  let emptyInVariant = 0
  for (let i = 1; i < refColors.length; i++) {
    if (refColors[i].toLowerCase() === bg) continue  // ref slot itself is empty, skip
    totalRefSlots++
    const varColor = variantColors[i]
    if (!varColor || varColor.toLowerCase() === bg) emptyInVariant++
  }
  const score = totalRefSlots === 0 ? 0 : emptyInVariant / totalRefSlots
  return { emptySlots: emptyInVariant, totalRefSlots, score }
}

// ---------------------------------------------------------------------------
// Mini swatch strip
// ---------------------------------------------------------------------------
function MiniStrip({ colors }) {
  return (
    <div className="mini-strip">
      {colors.slice(0, 8).map((c, i) => (
        <div key={i} className="mini-swatch" style={{ background: c }} />
      ))}
      {colors.length > 8 && (
        <span style={{ fontFamily: 'var(--mono)', fontSize: 8, color: 'var(--muted)', lineHeight: '8px' }}>
          +{colors.length - 8}
        </span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Slot match badge — shown in the card header
// ---------------------------------------------------------------------------
function SlotMatchBadge({ match }) {
  if (!match) return null
  const { score, emptySlots, totalRefSlots } = match
  if (score === 0) return null  // perfect — no badge needed

  const isRed    = score >= SLOT_ERROR_THRESHOLD
  const isYellow = score >= SLOT_WARN_THRESHOLD

  if (!isYellow) return null

  return (
    <span style={{
      fontFamily: 'var(--mono)', fontSize: 9, fontWeight: 500,
      color: isRed ? 'var(--danger)' : '#e3b341',
      whiteSpace: 'nowrap', flexShrink: 0,
      display: 'flex', alignItems: 'center', gap: 3,
    }}>
      <AlertTriangle size={9} />
      {emptySlots}/{totalRefSlots} empty slots
    </span>
  )
}

// ---------------------------------------------------------------------------
// Slot match warning block — shown below palette strip on flagged cards
// ---------------------------------------------------------------------------
function SlotMatchWarning({ match }) {
  if (!match) return null
  const { score, emptySlots, totalRefSlots } = match
  if (score < SLOT_WARN_THRESHOLD) return null

  const isRed = score >= SLOT_ERROR_THRESHOLD
  const pct   = Math.round(score * 100)

  return (
    <div className={`variant-match-warn ${isRed ? 'warn-red' : 'warn-yellow'}`}>
      <AlertTriangle size={11} style={{ flexShrink: 0, marginTop: 1 }} />
      <span>
        {emptySlots} of {totalRefSlots} reference slots are empty in this variant ({pct}%).
        {isRed
          ? ' This sprite may not share the same silhouette as the reference.'
          : ' Some areas of the reference have no corresponding pixels here.'}
      </span>
    </div>
  )
}

// ===========================================================================
// MODE 1 — Extract: N sprites → N index-aligned palettes
// ===========================================================================
function ExtractMode({ nColors, outputBg, outputBgMode, setOutputBg, setOutputBgMode }) {
  const [sprites, setSprites]       = useState([])
  const [refIndex, setRefIndex]     = useState(0)
  const [results, setResults]       = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [viewMode, setViewMode]     = useState('grid')
  const inputRef = useRef()

  // Dimension mismatch (size check, instant)
  const dimMismatches = useMemo(() => {
    if (sprites.length < 2) return new Set()
    const ref = sprites[refIndex]
    if (!ref) return new Set()
    const s = new Set()
    sprites.forEach((sp, i) => {
      if (i !== refIndex && (sp.w !== ref.w || sp.h !== ref.h)) s.add(sp.name)
    })
    return s
  }, [sprites, refIndex])

  const hasDimMismatch = dimMismatches.size > 0

  // Slot mismatch (computed from extraction results)
  const slotMatches = useMemo(() => {
    if (!results) return {}
    const refResult = results.results.find(r => r.name === results.reference)
    if (!refResult) return {}
    const out = {}
    results.results.forEach(r => {
      if (r.name === results.reference) return
      out[r.name] = computeSlotMatch(refResult.colors, r.colors, outputBg)
    })
    return out
  }, [results, outputBg])

  const handleFiles = async (fileList) => {
    const sorted = Array.from(fileList).sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
    )
    const loaded = await Promise.all(sorted.map(async f => {
      const b64     = await fileToB64(f)
      const inputBg = await detectBgColor(b64)
      const dims    = await getImageDimensions(b64)
      return { file: f, name: f.name.replace(/\.[^.]+$/, ''), b64, inputBg, w: dims.w, h: dims.h }
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
    setSprites(prev => {
      const next = prev.filter((_, i) => i !== idx)
      if (refIndex >= next.length)  setRefIndex(Math.max(0, next.length - 1))
      else if (idx < refIndex)      setRefIndex(r => r - 1)
      return next
    })
    setResults(null)
  }

  const handleSetRef = (idx) => { setRefIndex(idx); setResults(null) }

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

  const refSprite = sprites[refIndex]

  return (
    <div className="variants-layout">
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
          <>
            <div className="variants-sprite-queue">
              {sprites.map((s, i) => {
                const isRef      = i === refIndex
                const isMismatch = dimMismatches.has(s.name)
                return (
                  <div key={s.name} className={`variants-queue-row ${isRef ? 'is-ref' : ''} ${isMismatch ? 'dim-mismatch' : ''}`}>
                    <img src={`data:image/png;base64,${s.b64}`} alt={s.name} className="sprite-queue-thumb" />
                    <span className="sprite-queue-name" title={`${s.w}×${s.h}`}>{s.name}</span>
                    <span style={{
                      fontFamily: 'var(--mono)', fontSize: 9, flexShrink: 0, whiteSpace: 'nowrap',
                      color: isMismatch ? 'var(--danger)' : 'var(--muted)',
                    }}>
                      {s.w}×{s.h}
                    </span>
                    <BgColorCell color={s.inputBg} onChange={color => updateInputBg(i, color)} />
                    {isRef
                      ? <span className="variants-ref-badge">ref</span>
                      : <button className="variants-set-ref-btn" onClick={() => handleSetRef(i)}>set ref</button>
                    }
                    <button className="sprite-queue-btn danger" onClick={() => removeSprite(i)}><X size={10} /></button>
                  </div>
                )
              })}
            </div>

            <p className="variants-ref-hint">
              The <strong style={{ color: 'var(--accent)' }}>ref</strong> sprite sets the palette slot order.
              All other variants map their colors to matching slots.
            </p>

            {hasDimMismatch && (
              <div className="variants-dim-warn">
                <AlertTriangle size={12} style={{ flexShrink: 0 }} />
                <span>
                  {dimMismatches.size === 1
                    ? `${[...dimMismatches][0]} doesn't match ref size (${refSprite?.w}×${refSprite?.h})`
                    : `${dimMismatches.size} sprites don't match ref size (${refSprite?.w}×${refSprite?.h})`
                  } — extraction will fail
                </span>
              </div>
            )}
          </>
        )}

        <div className="field">
          <label className="field-label">output transparent (slot 0)</label>
          <BgColorPicker
            color={outputBg} mode={outputBgMode}
            onChange={({ color, mode }) => { setOutputBg(color); setOutputBgMode(mode) }}
          />
        </div>

        <button className="btn-primary" disabled={sprites.length < 1 || loading || hasDimMismatch} onClick={handleExtract}>
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
          <p>Mark one as the <strong>ref</strong> — it sets the slot order. Every other variant gets a palette where each slot maps to the color at the same pixel positions.</p>
          <p>Result: all palettes are index-compatible. Use the same sprite with any palette in-game.</p>
        </div>
      </div>

      <div className="variants-right">
        <div className="items-toolbar">
          <span className="items-count">
            {results ? `${results.results.length} variant${results.results.length !== 1 ? 's' : ''} · ref: ${results.reference}` : ''}
          </span>
          {results && <ViewToggle value={viewMode} onChange={setViewMode} />}
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
            {results.results.map(r => {
              const isRef = r.name === results.reference
              const match = isRef ? null : slotMatches[r.name]
              return (
                <div key={r.name} className={`variant-card ${isRef ? 'is-reference' : ''} ${viewMode === 'list' ? 'list-mode' : ''}`}>
                  {viewMode === 'list' ? (
                    <>
                      <div className="variant-card-preview">
                        <ZoomableImage src={r.preview} alt={r.name} />
                      </div>
                      <div className="variant-card-body">
                        <div className="variant-card-header">
                          <span className="variant-card-name">{r.name}</span>
                          {isRef && <span className="item-card-ref-badge">ref</span>}
                          <SlotMatchBadge match={match} />
                          <button className="sprite-queue-btn" onClick={() => downloadPal(r.pal_content, r.name)}>
                            <Download size={11} />
                          </button>
                        </div>
                        <PaletteStrip colors={r.colors} usedIndices={r.colors.map((_, i) => i)} checkSize="50%" />
                        <SlotMatchWarning match={match} />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="variant-card-header">
                        <span className="variant-card-name">{r.name}</span>
                        {isRef && <span className="item-card-ref-badge">ref</span>}
                        <SlotMatchBadge match={match} />
                      </div>
                      <PaletteStrip colors={r.colors} usedIndices={r.colors.map((_, i) => i)} checkSize="100%" />
                      <ZoomableImage src={r.preview} alt={r.name} />
                      <SlotMatchWarning match={match} />
                      <button className="btn-secondary" onClick={() => downloadPal(r.pal_content, r.name)}>
                        <Download size={11} /> download .pal
                      </button>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ===========================================================================
// MODE 2 — Apply: 1 sprite + N palettes → N recolored sprites
// ===========================================================================
function ApplyMode({ nColors, outputBg, outputBgMode, setOutputBg, setOutputBgMode }) {
  const [spriteFile, setSpriteFile]     = useState(null)
  const [spriteB64, setSpriteB64]       = useState(null)
  const [loadedPalettes, setLoadedPalettes] = useState([])
  const [selectedPals, setSelectedPals] = useState([])   // { name, colors }
  const [refPalName, setRefPalName]     = useState(null)
  const [results, setResults]           = useState([])   // { name, colors, preview }
  const [rendering, setRendering]       = useState(false)
  const [viewMode, setViewMode]         = useState('grid')
  const [downloading, setDownloading]   = useState(false)

  const spriteRef  = useRef()
  const palFileRef = useRef()

  useEffect(() => {
    fetch(`${API}/palettes`).then(r => r.json()).then(setLoadedPalettes).catch(() => {})
  }, [])

  // Re-render whenever sprite, ref palette, selected palettes or bg changes
  useEffect(() => {
    const refPal = selectedPals.find(p => p.name === refPalName)
    if (!spriteB64 || !refPal || selectedPals.length === 0) { setResults([]); return }

    setRendering(true)
    Promise.all(
      selectedPals.map(async pal => {
        const preview = await remapToShinyPalette(spriteB64, refPal.colors, pal.colors)
        return { name: pal.name.replace(/\.pal$/, ''), colors: pal.colors, preview, palName: pal.name }
      })
    ).then(r => { setResults(r); setRendering(false) })
  }, [spriteB64, refPalName, selectedPals, outputBg])

  // Slot mismatch: compare each non-ref variant's palette against the ref palette
  const slotMatches = useMemo(() => {
    const refPal = selectedPals.find(p => p.name === refPalName)
    if (!refPal) return {}
    const out = {}
    selectedPals.forEach(pal => {
      if (pal.name === refPalName) return
      out[pal.name] = computeSlotMatch(refPal.colors, pal.colors, outputBg)
    })
    return out
  }, [selectedPals, refPalName, outputBg])

  const handleSprite = async (f) => {
    setSpriteFile(f)
    const b64 = await fileToB64(f)
    setSpriteB64(b64)
    setResults([])
  }

  const toggleLoadedPal = (pal) => {
    setSelectedPals(prev => {
      const exists = prev.find(p => p.name === pal.name)
      if (exists) {
        if (refPalName === pal.name) setRefPalName(null)
        return prev.filter(p => p.name !== pal.name)
      }
      return [...prev, { name: pal.name, colors: pal.colors }]
    })
  }

  const handleImportPalFile = (e) => {
    Array.from(e.target.files).forEach(f => {
      const reader = new FileReader()
      reader.onload = ev => {
        const colors = parsePalFile(ev.target.result)
        if (colors.length > 0) {
          const name = f.name
          setSelectedPals(prev => prev.find(p => p.name === name) ? prev : [...prev, { name, colors }])
        }
      }
      reader.readAsText(f)
    })
    e.target.value = ''
  }

  const removeSelectedPal = (name) => {
    setSelectedPals(prev => prev.filter(p => p.name !== name))
    if (refPalName === name) setRefPalName(null)
  }

  const handleDownloadAll = async () => {
    if (results.length === 0) return
    setDownloading(true)
    try {
      // Build zip client-side using a simple approach: one fetch per image blob
      const zipEntries = []
      for (const r of results) {
        const imgRes  = await fetch(`data:image/png;base64,${r.preview}`)
        const imgBlob = await imgRes.blob()
        zipEntries.push({ path: `sprites/${r.name}.png`, blob: imgBlob })

        // Also write the palette
        const palObj = selectedPals.find(p => p.name === r.palName || p.name.replace(/\.pal$/, '') === r.name)
        if (palObj) {
          const lines = ['JASC-PAL', '0100', String(palObj.colors.length),
            ...palObj.colors.map(h => {
              const hx = h.replace('#', '')
              return `${parseInt(hx.slice(0,2),16)} ${parseInt(hx.slice(2,4),16)} ${parseInt(hx.slice(4,6),16)}`
            })]
          const palBlob = new Blob([lines.join('\n') + '\n'], { type: 'text/plain' })
          zipEntries.push({ path: `palettes/${r.name}.pal`, blob: palBlob })
        }
      }

      const manifest = {
        reference_palette: refPalName ?? '',
        sprite: spriteFile?.name ?? '',
        files: results.map(r => ({
          name:    r.name,
          sprite:  `sprites/${r.name}.png`,
          palette: `palettes/${r.name}.pal`,
        })),
      }
      const manifestBlob = new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' })
      zipEntries.push({ path: 'manifest.json', blob: manifestBlob })

      // Use the existing download-all zip endpoint pattern:
      // We can't use JSZip without installing it, so POST to the backend instead.
      // Build a FormData with all images + palettes and use the shiny apply/download endpoint
      // which already does this. But we have N palettes here, not just 2.
      // Simpler: post to a new endpoint. For now, download individually if zip unavailable.
      // Actually — use the browser's native approach: create a zip via the backend
      // by posting the sprite + all palettes.
      const fd = new FormData()
      if (spriteFile) fd.append('sprite_file', spriteFile)
      const refPal = selectedPals.find(p => p.name === refPalName)
      if (refPal) fd.append('ref_pal', JSON.stringify(refPal.colors))
      selectedPals.forEach(p => {
        fd.append('pal_names', p.name.replace(/\.pal$/, ''))
        fd.append('pal_colors', JSON.stringify(p.colors))
      })

      const res = await fetch(`${API}/items/apply-variants/download`, { method: 'POST', body: fd })
      if (res.ok) {
        const stem = spriteFile?.name.replace(/\.[^.]+$/, '') ?? 'sprite'
        downloadBlob(await res.blob(), `${stem}_variants.zip`)
      }
    } finally {
      setDownloading(false)
    }
  }

  const refPal = selectedPals.find(p => p.name === refPalName)

  return (
    <div className="variants-layout">
      <div className="variants-left">
        {/* Sprite drop */}
        <div
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleSprite(f) }}
        >
          <div className="dropzone" onClick={() => spriteRef.current?.click()}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--muted)' }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p className="dropzone-label">{spriteFile ? spriteFile.name : 'Drop base sprite'}</p>
            <p className="dropzone-hint">one sprite · apply N palettes</p>
          </div>
          <input ref={spriteRef} type="file" accept="image/*" style={{ display: 'none' }}
            onChange={e => { if (e.target.files[0]) handleSprite(e.target.files[0]); e.target.value = '' }} />
        </div>

        {/* Output bg */}
        <div className="field">
          <label className="field-label">output transparent (slot 0)</label>
          <BgColorPicker
            color={outputBg} mode={outputBgMode}
            onChange={({ color, mode }) => { setOutputBg(color); setOutputBgMode(mode) }}
          />
        </div>

        {/* Palette queue */}
        <div className="field">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <label className="field-label">palettes ({selectedPals.length})</label>
            <button
              className="bg-mode-btn"
              style={{ display: 'flex', alignItems: 'center', gap: 4 }}
              onClick={() => palFileRef.current?.click()}
            >
              <Upload size={9} /> import .pal
            </button>
            <input ref={palFileRef} type="file" accept=".pal" multiple style={{ display: 'none' }}
              onChange={handleImportPalFile} />
          </div>

          {selectedPals.length > 0 && (
            <div className="variants-sprite-queue" style={{ marginBottom: 6 }}>
              {selectedPals.map(pal => {
                const isRef = pal.name === refPalName
                return (
                  <div key={pal.name} className={`variants-queue-row ${isRef ? 'is-ref' : ''}`}>
                    <span className="sprite-queue-name">{pal.name.replace(/\.pal$/, '')}</span>
                    <MiniStrip colors={pal.colors} />
                    {isRef
                      ? <span className="variants-ref-badge">ref</span>
                      : <button className="variants-set-ref-btn" onClick={() => setRefPalName(pal.name)}>set ref</button>
                    }
                    <button className="sprite-queue-btn danger" onClick={() => removeSelectedPal(pal.name)}>
                      <X size={10} />
                    </button>
                  </div>
                )
              })}
            </div>
          )}

          {/* Loaded palettes picker */}
          {loadedPalettes.length > 0 && (
            <>
              <span className="field-label" style={{ marginBottom: 4, display: 'block' }}>add from loaded</span>
              <div className="apply-pal-picker">
                {loadedPalettes.map(p => {
                  const checked = !!selectedPals.find(s => s.name === p.name)
                  return (
                    <div
                      key={p.name}
                      className={`apply-pal-pick-row ${checked ? 'checked' : ''}`}
                      onClick={() => toggleLoadedPal(p)}
                    >
                      <span className="apply-pal-pick-name">{p.name.replace(/\.pal$/, '')}</span>
                      <MiniStrip colors={p.colors} />
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>

        {selectedPals.length > 0 && !refPalName && (
          <p style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#e3b341' }}>
            ⚠ Set one palette as ref — it defines which pixel maps to which slot.
          </p>
        )}

        {results.length > 0 && (
          <button className="btn-secondary" disabled={downloading} onClick={handleDownloadAll}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Download size={11} /> {downloading ? 'zipping…' : 'download all as zip'}
          </button>
        )}

        <div className="variants-explainer">
          <p className="section-label">how it works</p>
          <p>Drop one base sprite and pick N palettes. Mark one as the <strong>ref</strong> — it defines how the sprite's colors map to palette slots.</p>
          <p>Every other palette is applied to the same sprite using that slot mapping, producing N recolored variants.</p>
        </div>
      </div>

      <div className="variants-right">
        <div className="items-toolbar">
          <span className="items-count">
            {results.length > 0 ? `${results.length} variant${results.length !== 1 ? 's' : ''}${refPalName ? ` · ref: ${refPalName.replace(/\.pal$/, '')}` : ''}` : ''}
          </span>
          {results.length > 0 && <ViewToggle value={viewMode} onChange={setViewMode} />}
        </div>

        {!spriteB64 && (
          <div className="empty-state">
            <p>drop a base sprite, then pick palettes and set a ref</p>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              the ref palette defines the slot order — all others remap to match
            </p>
          </div>
        )}
        {spriteB64 && selectedPals.length === 0 && (
          <div className="empty-state"><p>add palettes on the left to generate variants</p></div>
        )}
        {spriteB64 && selectedPals.length > 0 && !refPalName && (
          <div className="empty-state"><p>set a ref palette to start rendering</p></div>
        )}
        {rendering && (
          <div className="empty-state"><div className="spinner" /><p>rendering variants…</p></div>
        )}

        {!rendering && results.length > 0 && (
          <div className={viewMode === 'grid' ? 'variants-results-grid' : 'variants-results-list'}>
            {results.map(r => {
              const isRef = r.palName === refPalName
              const match = isRef ? null : slotMatches[r.palName]
              return (
                <div key={r.name} className={`variant-card ${isRef ? 'is-reference' : ''} ${viewMode === 'list' ? 'list-mode' : ''}`}>
                  {viewMode === 'list' ? (
                    <>
                      <div className="variant-card-preview">
                        <ZoomableImage src={r.preview} alt={r.name} />
                      </div>
                      <div className="variant-card-body">
                        <div className="variant-card-header">
                          <span className="variant-card-name">{r.name}</span>
                          {isRef && <span className="item-card-ref-badge">ref</span>}
                          <SlotMatchBadge match={match} />
                        </div>
                        <PaletteStrip colors={r.colors} usedIndices={r.colors.map((_, i) => i)} checkSize="50%" />
                        <SlotMatchWarning match={match} />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="variant-card-header">
                        <span className="variant-card-name">{r.name}</span>
                        {isRef && <span className="item-card-ref-badge">ref</span>}
                        <SlotMatchBadge match={match} />
                      </div>
                      <PaletteStrip colors={r.colors} usedIndices={r.colors.map((_, i) => i)} checkSize="100%" />
                      <ZoomableImage src={r.preview} alt={r.name} />
                      <SlotMatchWarning match={match} />
                    </>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ===========================================================================
// Root export — mode switcher wrapping both modes
// ===========================================================================
export function VariantsPanel({ nColors, outputBg, outputBgMode, setOutputBg, setOutputBgMode }) {
  const [mode, setMode] = useState('extract')

  return (
    <div>
      <div className="variants-mode-switcher">
        <button
          className={`variants-mode-btn ${mode === 'extract' ? 'active' : ''}`}
          onClick={() => setMode('extract')}
        >
          extract palettes
        </button>
        <button
          className={`variants-mode-btn ${mode === 'apply' ? 'active' : ''}`}
          onClick={() => setMode('apply')}
        >
          apply palettes
        </button>
      </div>

      {mode === 'extract' && (
        <ExtractMode
          nColors={nColors}
          outputBg={outputBg}
          outputBgMode={outputBgMode}
          setOutputBg={setOutputBg}
          setOutputBgMode={setOutputBgMode}
        />
      )}
      {mode === 'apply' && (
        <ApplyMode
          nColors={nColors}
          outputBg={outputBg}
          outputBgMode={outputBgMode}
          setOutputBg={setOutputBg}
          setOutputBgMode={setOutputBgMode}
        />
      )}
    </div>
  )
}