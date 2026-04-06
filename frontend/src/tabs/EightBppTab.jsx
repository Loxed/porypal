/**
 * frontend/src/tabs/EightBppTab.jsx
 *
 * Mode A "View"   — load 8bpp indexed PNG → preview + palette grid → optional shrink
 * Mode B "Create" — load any image → generate 8bpp palette via greedy-merge + k-medoids
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { Download, Save, Check, X, Grid2x2, Pipette, Wand2, Eye } from 'lucide-react'
import { DropZone } from '../components/DropZone'
import { HighlightableImage } from '../components/HighlightableImage'
import { BeforeAfter } from '../components/BeforeAfter'
import './EightBppTab.css'

const API = '/api'

// ── Shared: Tooltip ───────────────────────────────────────────────────────────

function HexTip({ hex, x, y, count }) {
  if (!hex) return null
  return (
    <div className="swatch-hex-tip" style={{ left: x + 14, top: y + 14 }}>
      <div className="swatch-hex-tip-dot" style={{ background: hex }} />
      {hex.toUpperCase()}
      {count > 0 && <span style={{ color: 'var(--muted)', marginLeft: 6 }}>{count.toLocaleString()}px</span>}
    </div>
  )
}

// ── Shared: Bank row ──────────────────────────────────────────────────────────

function BankRow({ bank, selected, onSelect, onHoverColors, highlightHex, pixelCounts }) {
  const [tip, setTip]    = useState(null)
  const bankColorSet     = new Set(bank.colors.map(c => c.hex.toLowerCase()))

  return (
    <div className={`palette-bank-row ${selected === false ? 'dimmed' : ''}`}>
      <div
        className={`bank-label ${selected ? 'selected' : ''}`}
        title={`Bank ${bank.bank} — ${bank.used_colors} colors`}
        onClick={onSelect}
        onMouseEnter={() => onHoverColors(bankColorSet)}
        onMouseLeave={() => onHoverColors(null)}
      >
        {bank.bank}
      </div>
      <div className="bank-swatches">
        {bank.colors.map(c => {
          const isMatch = highlightHex && c.hex.toLowerCase() === highlightHex.toLowerCase()
          const count   = pixelCounts?.get(c.hex.toLowerCase()) ?? 0
          const ringColor = (() => {
            const h = c.hex.replace('#','')
            const r = parseInt(h.slice(0,2),16)/255
            const g = parseInt(h.slice(2,4),16)/255
            const b = parseInt(h.slice(4,6),16)/255
            return (0.2126*r + 0.7152*g + 0.0722*b) > 0.35 ? '#000' : '#fff'
          })()
          return (
            <div
              key={c.slot}
              className={`color-swatch-256 ${isMatch ? 'pipette-match' : ''}`}
              style={{ background: c.hex, ...(isMatch ? { outlineColor: ringColor } : {}) }}
              onMouseEnter={e => {
                setTip({ hex: c.hex, x: e.clientX, y: e.clientY, count })
                onHoverColors(new Set([c.hex.toLowerCase()]))
              }}
              onMouseMove={e => setTip({ hex: c.hex, x: e.clientX, y: e.clientY, count })}
              onMouseLeave={() => { setTip(null); onHoverColors(null) }}
              onClick={() => navigator.clipboard?.writeText(c.hex)}
              title={`[${c.index}] ${c.hex}${count ? ' · ' + count + 'px' : ''}${isMatch ? ' ← pipette' : ''}`}
            >
              {count > 0 && pixelCounts && (
                <span className="swatch-count">
                  {count >= 1000 ? Math.round(count/1000)+'k' : count}
                </span>
              )}
            </div>
          )
        })}
      </div>
      {tip && <HexTip hex={tip.hex} x={tip.x} y={tip.y} count={tip.count} />}
    </div>
  )
}

// ── Shared: Bank detail ───────────────────────────────────────────────────────

function BankDetail({ bank, fileName, allColors, onHoverColors }) {
  const [saveState, setSaveState] = useState('idle')
  const [saveName, setSaveName]   = useState('')
  if (!bank) return null

  const displayName = saveName || `${fileName}_bank${bank.bank}`
  const buildFd = () => {
    const fd = new FormData()
    fd.append('file', new File([''], 'dummy.pal'))
    fd.append('bank_index', String(bank.bank))
    fd.append('name', displayName)
    fd.append('colors_json', JSON.stringify(allColors.map(c => c.hex)))
    return fd
  }

  const doDownload = async () => {
    const res = await fetch(`${API}/8bpp/export-bank`, { method: 'POST', body: buildFd() })
    if (!res.ok) return
    const a = document.createElement('a')
    a.href = URL.createObjectURL(await res.blob())
    a.download = `${displayName}.pal`
    a.click()
  }

  const doSave = async () => {
    if (saveState === 'saving') return
    setSaveState('saving')
    try {
      const res  = await fetch(`${API}/8bpp/export-bank`, { method: 'POST', body: buildFd() })
      if (!res.ok) throw new Error()
      const text = await res.blob().then(b => b.text())
      const fd2  = new FormData()
      fd2.append('file', new File([text], `${displayName}.pal`, { type: 'text/plain' }))
      if (!(await fetch(`${API}/palettes/upload`, { method: 'POST', body: fd2 })).ok) throw new Error()
      setSaveState('saved'); setTimeout(() => setSaveState('idle'), 2000)
    } catch { setSaveState('error'); setTimeout(() => setSaveState('idle'), 2000) }
  }

  return (
    <div className="bank-detail">
      <div className="bank-detail-header">
        <span className="bank-detail-title">bank {bank.bank}</span>
        <span className="bank-detail-meta">
          indices {bank.bank*16}–{bank.bank*16+15} · {bank.used_colors} colors used
        </span>
      </div>
      <div className="bank-detail-body">
        <div className="bank-detail-strip">
          {bank.colors.map(c => (
            <div key={c.slot} className="bank-detail-swatch" style={{ background: c.hex }}
              title={`slot ${c.slot} · ${c.hex}`}
              onMouseEnter={() => onHoverColors(new Set([c.hex.toLowerCase()]))}
              onMouseLeave={() => onHoverColors(null)}
              onClick={() => navigator.clipboard?.writeText(c.hex)}>
              <span className="slot-num">{c.slot}</span>
            </div>
          ))}
        </div>
        <div className="bank-detail-actions">
          <div className="field" style={{ flex:1, gap:4 }}>
            <label className="field-label">export name</label>
            <input className="field-input" value={saveName}
              onChange={e => setSaveName(e.target.value)}
              placeholder={displayName} spellCheck={false} />
          </div>
          <div style={{ display:'flex', gap:6, alignSelf:'flex-end' }}>
            <button className="bank-export-btn" onClick={doDownload}>
              <Download size={12} /> download
            </button>
            <button className={`bank-save-btn ${saveState}`} onClick={doSave} disabled={saveState==='saving'}>
              {saveState==='saved' ? <><Check size={12}/> saved</>
               : saveState==='error' ? <><X size={12}/> failed</>
               : <><Save size={12}/> save to library</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Shared: Palette grid + sprite preview panel ───────────────────────────────

function PalettePanel({
  result, spriteUrl, spriteFile, beforeUrl,
  pipetteActive, setPipetteActive,
  pipetteHex, setPipetteHex,
  hoverColors, setHoverColors,
  filterBank, setFilterBank,
  selectedBank, setSelectedBank,
  pixelCounts,
  children,   // slot for metrics / action buttons above palette
}) {
  const filterColors = filterBank !== null && result
    ? new Set(result.banks[filterBank].colors.map(c => c.hex.toLowerCase()))
    : null
  const activeHighlight = pipetteActive && pipetteHex
    ? new Set([pipetteHex.toLowerCase()])
    : (hoverColors ?? filterColors)
  const allColors = result ? result.banks.flatMap(b => b.colors) : []

  const handlePipette = (hex) => {
    setPipetteHex(hex || null)
    setHoverColors(hex ? new Set([hex.toLowerCase()]) : null)
  }
  const handleBankClick = (bank) =>
    setSelectedBank(prev => prev?.bank === bank.bank ? null : bank)
  const handleFilterClick = (bankIndex) => {
    const isOff = filterBank === bankIndex
    setFilterBank(isOff ? null : bankIndex)
    if (result && !isOff) setSelectedBank(result.banks[bankIndex])
  }

  return (
    <>
      {/* Sprite */}
      {spriteUrl && result && (
        <div>
          <p className="section-label" style={{ marginBottom:6 }}>
            sprite
            {beforeUrl && <span className="label-accent"> · drag to compare</span>}
            {!beforeUrl && pipetteActive && <span className="label-accent"> · hover to identify color</span>}
            {!beforeUrl && !pipetteActive && activeHighlight &&
              <span className="label-accent"> · {activeHighlight.size} color{activeHighlight.size!==1?'s':''} highlighted</span>}
          </p>
          {beforeUrl
            ? <BeforeAfter before={beforeUrl} after={spriteUrl} alt={spriteFile?.name ?? ''} />
            : <HighlightableImage
                src={spriteUrl} alt={spriteFile?.name ?? ''}
                highlightColors={activeHighlight}
                pipetteActive={pipetteActive}
                onPipette={handlePipette}
              />
          }
        </div>
      )}

      {/* Metrics / actions slot */}
      {children}

      {/* Toolbar */}
      <div className="eightbpp-toolbar">
        <span className="section-label">
          {result
            ? `${result.name} · ${result.total_colors} colors · ${result.used_banks} banks used`
            : '256-color palette'}
        </span>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          {spriteUrl && result && !beforeUrl && (
            <button
              className={`bank-filter-btn ${pipetteActive ? 'active' : ''}`}
              style={{ width:'auto', padding:'4px 10px', gap:5, display:'flex', alignItems:'center' }}
              onClick={() => { setPipetteActive(p=>!p); setPipetteHex(null); setHoverColors(null) }}
              title="Hover sprite to identify colors"
            >
              <Pipette size={11} /> pipette
            </button>
          )}
          {result && <span className="eightbpp-meta-badge">16 × 16</span>}
        </div>
      </div>

      {/* Bank filter */}
      {result && (
        <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
          <div className="bank-filter-row">
            <button
              className={`bank-filter-btn bank-filter-all ${filterBank===null?'active':''}`}
              onClick={() => setFilterBank(null)}>all</button>
            {result.banks.map(b => (
              <button key={b.bank}
                className={`bank-filter-btn ${filterBank===b.bank?'active':''} ${b.used_colors===0?'empty':''}`}
                onClick={() => handleFilterClick(b.bank)}
                onMouseEnter={() => !pipetteActive && setHoverColors(new Set(b.colors.map(c=>c.hex.toLowerCase())))}
                onMouseLeave={() => !pipetteActive && setHoverColors(null)}
                title={`Bank ${b.bank} · ${b.used_colors} colors`}
              >{b.bank}</button>
            ))}
          </div>
        </div>
      )}

      {/* Grid */}
      {result && (
        <div>
          <p className="section-label" style={{ marginBottom:6 }}>
            palette — hover to highlight · click row to inspect
            {pipetteHex && pipetteActive &&
              <span className="label-accent"> · {pipetteHex.toUpperCase()}</span>}
          </p>
          <div className="palette-256-grid">
            {result.banks.map(bank => (
              <BankRow key={bank.bank} bank={bank}
                selected={filterBank===null
                  ? selectedBank?.bank===bank.bank||null
                  : filterBank===bank.bank?true:false}
                onSelect={() => handleBankClick(bank)}
                onHoverColors={pipetteActive ? ()=>{} : setHoverColors}
                highlightHex={pipetteActive ? pipetteHex : null}
                pixelCounts={pixelCounts}
              />
            ))}
          </div>
        </div>
      )}

      {/* Bank detail */}
      {selectedBank && result && (
        <BankDetail bank={selectedBank} fileName={result.name}
          allColors={allColors}
          onHoverColors={pipetteActive ? ()=>{} : setHoverColors} />
      )}
    </>
  )
}

// ── Mode A: View ──────────────────────────────────────────────────────────────

function ModeView() {
  const [spriteFile, setSpriteFile]   = useState(null)
  const [spriteUrl, setSpriteUrl]     = useState(null)
  const [palFile, setPalFile]         = useState(null)
  const [result, setResult]           = useState(null)
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)

  // shrink
  const [shrinking, setShrinking]     = useState(false)
  const [shrinkResult, setShrinkResult] = useState(null)  // { result, image_b64, metrics }
  const [threshold, setThreshold]     = useState(0.05)
  const [showShrink, setShowShrink]   = useState(false)

  // palette panel state
  const [pipetteActive, setPipetteActive] = useState(false)
  const [pipetteHex, setPipetteHex]       = useState(null)
  const [hoverColors, setHoverColors]     = useState(null)
  const [filterBank, setFilterBank]       = useState(null)
  const [selectedBank, setSelectedBank]   = useState(null)
  const [pixelCounts, setPixelCounts]     = useState(null)

  const spriteUrlRef = useRef(null)

  // active display: shrink result overrides original
  const displayUrl    = shrinkResult ? `data:image/png;base64,${shrinkResult.image_b64}` : spriteUrl
  const displayResult = shrinkResult?.result ?? result

  useEffect(() => {
    if (!displayUrl) { setPixelCounts(null); return }
    const img = new window.Image()
    img.onload = () => {
      const off = document.createElement('canvas')
      off.width = img.naturalWidth; off.height = img.naturalHeight
      const ctx = off.getContext('2d'); ctx.drawImage(img, 0, 0)
      const { data } = ctx.getImageData(0, 0, off.width, off.height)
      const counts = new Map()
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) continue
        const hex = '#' + data[i].toString(16).padStart(2,'0')
          + data[i+1].toString(16).padStart(2,'0')
          + data[i+2].toString(16).padStart(2,'0')
        counts.set(hex, (counts.get(hex) ?? 0) + 1)
      }
      setPixelCounts(counts)
    }
    img.src = displayUrl
  }, [displayUrl])

  const loadSprite = async (f) => {
    setSpriteFile(f)
    const url = URL.createObjectURL(f)
    setSpriteUrl(url); spriteUrlRef.current = url
    setShrinkResult(null)
    setPipetteHex(null); setPipetteActive(false)
    setError(null); setLoading(true)
    try {
      const fd = new FormData(); fd.append('file', f)
      let res  = await fetch(`${API}/8bpp/load`, { method:'POST', body:fd })
      if (!res.ok) {
        // Not indexed — just show sprite, no palette
        setResult(null)
        return
      }
      setResult(await res.json())
      setShrinkResult(null)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const loadPal = async (f) => {
    setPalFile(f); setError(null); setLoading(true)
    try {
      const fd = new FormData(); fd.append('file', f)
      const res = await fetch(`${API}/8bpp/load`, { method:'POST', body:fd })
      if (!res.ok) throw new Error(await res.text())
      setResult(await res.json()); setShrinkResult(null)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const doShrink = async () => {
    if (!spriteFile || shrinking) return
    setShrinking(true)
    try {
      const fd = new FormData()
      fd.append('file', spriteFile)
      fd.append('threshold', String(threshold))
      fd.append('max_colors', '256')
      const res = await fetch(`${API}/8bpp/shrink`, { method:'POST', body:fd })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setShrinkResult({ result: data, image_b64: data.image_b64, metrics: data.metrics })
    } catch (e) { setError(e.message) }
    finally { setShrinking(false) }
  }

  const metrics = shrinkResult?.metrics

  return (
    <div className="eightbpp-right">
      {/* Drop zones */}
      <div className="dual-dropzone">
        <div className="dual-dropzone-slot">
          <p className="section-label" style={{ marginBottom:6 }}>sprite (8bpp PNG)</p>
          <DropZone onFile={loadSprite} accept="image/*"
            label={spriteFile ? spriteFile.name : 'drop image'} />
        </div>
        <div className="dual-dropzone-slot">
          <p className="section-label" style={{ marginBottom:6 }}>palette override</p>
          <DropZone onFile={loadPal} accept=".pal"
            label={palFile ? palFile.name : 'drop .pal'} />
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      {loading && <div className="empty-state"><div className="spinner"/><p>loading…</p></div>}

      {/* Shrink controls — only if sprite is an 8bpp indexed PNG */}
      {spriteFile && result && !loading && (
        <div className="shrink-panel">
          <div className="shrink-header" onClick={() => setShowShrink(s=>!s)}>
            <span className="section-label" style={{ cursor:'pointer' }}>
              ▸ shrink palette
            </span>
            {metrics && (
              <span className="shrink-metrics">
                {metrics.original} → {metrics.after_merge}
                {metrics.after_reduce !== metrics.after_merge && ` → ${metrics.after_reduce}`}
                {' '}colors
              </span>
            )}
          </div>
          {showShrink && (
            <div className="shrink-body">
              <div style={{ display:'flex', alignItems:'center', gap:12 }}>
                <label className="field-label">merge threshold</label>
                <input type="range" min="0.01" max="0.2" step="0.01"
                  value={threshold}
                  onChange={e => { setThreshold(parseFloat(e.target.value)); setShrinkResult(null) }}
                  style={{ flex:1 }} />
                <span className="shrink-threshold-val">{threshold.toFixed(2)}</span>
              </div>
              <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                <button className={`bank-export-btn ${shrinking?'':'active-ish'}`}
                  onClick={doShrink} disabled={shrinking}>
                  <Wand2 size={11}/>
                  {shrinking ? ' shrinking…' : ' run shrink'}
                </button>
                {shrinkResult && (
                  <button className="bank-filter-btn"
                    onClick={() => setShrinkResult(null)}
                    title="Restore original">
                    <Eye size={11}/>
                  </button>
                )}
                {shrinkResult && (
                  <a
                    href={`data:image/png;base64,${shrinkResult.image_b64}`}
                    download={`${result.name}_shrunk.png`}
                    className="bank-export-btn"
                  >
                    <Download size={11}/> save PNG
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {!spriteFile && !loading && (
        <div className="empty-state">
          <Eye size={28} style={{ color:'var(--border2)' }}/>
          <p>drop an 8bpp indexed PNG to preview</p>
        </div>
      )}

      <PalettePanel
        result={displayResult} spriteUrl={displayUrl} spriteFile={spriteFile}
        beforeUrl={shrinkResult ? spriteUrl : null}
        pipetteActive={pipetteActive} setPipetteActive={setPipetteActive}
        pipetteHex={pipetteHex} setPipetteHex={setPipetteHex}
        hoverColors={hoverColors} setHoverColors={setHoverColors}
        filterBank={filterBank} setFilterBank={setFilterBank}
        selectedBank={selectedBank} setSelectedBank={setSelectedBank}
        pixelCounts={pixelCounts}
      />
    </div>
  )
}

// ── Mode B: Create ────────────────────────────────────────────────────────────

function ModeCreate() {
  const [imageFile, setImageFile]     = useState(null)
  const [imageUrl, setImageUrl]       = useState(null)
  const [result, setResult]           = useState(null)   // { ...banks, image_b64, metrics }
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [nColors, setNColors]         = useState(255)
  const [threshold, setThreshold]     = useState(0.05)

  const [pipetteActive, setPipetteActive] = useState(false)
  const [pipetteHex, setPipetteHex]       = useState(null)
  const [hoverColors, setHoverColors]     = useState(null)
  const [filterBank, setFilterBank]       = useState(null)
  const [selectedBank, setSelectedBank]   = useState(null)
  const [pixelCounts, setPixelCounts]     = useState(null)

  const quantizedUrl = result ? `data:image/png;base64,${result.image_b64}` : null
  const displayUrl   = quantizedUrl ?? imageUrl

  useEffect(() => {
    if (!displayUrl) { setPixelCounts(null); return }
    const img = new window.Image()
    img.onload = () => {
      const off = document.createElement('canvas')
      off.width = img.naturalWidth; off.height = img.naturalHeight
      const ctx = off.getContext('2d'); ctx.drawImage(img, 0, 0)
      const { data } = ctx.getImageData(0, 0, off.width, off.height)
      const counts = new Map()
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) continue
        const hex = '#' + data[i].toString(16).padStart(2,'0')
          + data[i+1].toString(16).padStart(2,'0')
          + data[i+2].toString(16).padStart(2,'0')
        counts.set(hex, (counts.get(hex) ?? 0) + 1)
      }
      setPixelCounts(counts)
    }
    img.src = displayUrl
  }, [displayUrl])

  const handleDrop = (f) => {
    setImageFile(f)
    setImageUrl(URL.createObjectURL(f))
    setResult(null); setError(null)
  }

  const doCreate = async () => {
    if (!imageFile || loading) return
    setLoading(true); setError(null)
    try {
      const fd = new FormData()
      fd.append('file', imageFile)
      fd.append('n_colors', String(nColors))
      fd.append('threshold', String(threshold))
      const res = await fetch(`${API}/8bpp/create`, { method:'POST', body:fd })
      if (!res.ok) throw new Error(await res.text())
      setResult(await res.json())
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const metrics = result?.metrics

  return (
    <div className="eightbpp-right">
      <div className="dual-dropzone" style={{ gridTemplateColumns:'1fr' }}>
        <div className="dual-dropzone-slot">
          <p className="section-label" style={{ marginBottom:6 }}>source image</p>
          <DropZone onFile={handleDrop} accept="image/*"
            label={imageFile ? imageFile.name : 'drop any image'} />
        </div>
      </div>

      {/* Controls */}
      {imageFile && (
        <div className="shrink-panel">
          <div className="shrink-body">
            <div style={{ display:'flex', alignItems:'center', gap:12 }}>
              <label className="field-label" style={{ whiteSpace:'nowrap' }}>max colors</label>
              <input type="range" min="16" max="255" step="1"
                value={nColors} onChange={e => setNColors(parseInt(e.target.value))}
                style={{ flex:1 }} />
              <span className="shrink-threshold-val">{nColors}</span>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:12 }}>
              <label className="field-label" style={{ whiteSpace:'nowrap' }}>merge threshold</label>
              <input type="range" min="0.01" max="0.2" step="0.01"
                value={threshold} onChange={e => setThreshold(parseFloat(e.target.value))}
                style={{ flex:1 }} />
              <span className="shrink-threshold-val">{threshold.toFixed(2)}</span>
            </div>
            <div style={{ display:'flex', gap:8, alignItems:'center' }}>
              <button className="bank-export-btn" onClick={doCreate} disabled={loading}>
                <Wand2 size={11}/>{loading ? ' creating…' : ' create palette'}
              </button>
              {metrics && (
                <span className="shrink-metrics">
                  {metrics.original} unique → {metrics.after_merge} merged → {metrics.after_reduce} final
                </span>
              )}
              {result && (
                <a href={quantizedUrl} download={`${result.name}_8bpp.png`}
                  className="bank-export-btn">
                  <Download size={11}/> save PNG
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {error && <p className="error-msg">{error}</p>}
      {loading && <div className="empty-state"><div className="spinner"/><p>generating palette…</p></div>}

      {!imageFile && (
        <div className="empty-state">
          <Wand2 size={28} style={{ color:'var(--border2)' }}/>
          <p>drop any image to generate a 256-color palette</p>
          <p style={{ fontSize:11, color:'var(--muted)', marginTop:4 }}>
            greedy merge + k-medoids · Oklab perceptual distance
          </p>
        </div>
      )}

      <PalettePanel
        result={result} spriteUrl={displayUrl} spriteFile={imageFile}
        pipetteActive={pipetteActive} setPipetteActive={setPipetteActive}
        pipetteHex={pipetteHex} setPipetteHex={setPipetteHex}
        hoverColors={hoverColors} setHoverColors={setHoverColors}
        filterBank={filterBank} setFilterBank={setFilterBank}
        selectedBank={selectedBank} setSelectedBank={setSelectedBank}
        pixelCounts={pixelCounts}
      />
    </div>
  )
}

// ── Main Tab ──────────────────────────────────────────────────────────────────

export function EightBppTab() {
  const [mode, setMode] = useState('view')  // 'view' | 'create'

  return (
    <div className="tab-content">
      <div className="eightbpp-layout">

        {/* Left: mode switcher + info */}
        <div className="eightbpp-left">
          <div className="mode-switcher">
            <button
              className={`mode-btn ${mode==='view'?'active':''}`}
              onClick={() => setMode('view')}
            >
              <Eye size={13}/>
              <span>view</span>
            </button>
            <button
              className={`mode-btn ${mode==='create'?'active':''}`}
              onClick={() => setMode('create')}
            >
              <Wand2 size={13}/>
              <span>create</span>
            </button>
          </div>

          <div className="eightbpp-info">
            {mode === 'view' ? <>
              <p className="section-label" style={{ marginBottom:4 }}>view mode</p>
              <p>Load an <strong style={{color:'var(--text)'}}>8bpp indexed PNG</strong> to preview it with its embedded 256-color palette.</p>
              <p>Drop a <code>.pal</code> override to swap the palette without changing the sprite.</p>
              <p><strong style={{color:'var(--text)'}}>Shrink</strong> merges near-identical colors (Oklab) and re-renders the image.</p>
            </> : <>
              <p className="section-label" style={{ marginBottom:4 }}>create mode</p>
              <p>Load <strong style={{color:'var(--text)'}}>any image</strong> to generate an optimized 256-color 8bpp palette.</p>
              <p>Uses greedy merge to collapse near-identical colors, then k-medoids clustering to hit the target count.</p>
              <p>Download the quantized PNG or export individual banks as <code>.pal</code>.</p>
            </>}
          </div>
        </div>

        {/* Right: mode content */}
        {mode === 'view'   && <ModeView />}
        {mode === 'create' && <ModeCreate />}

      </div>
    </div>
  )
}