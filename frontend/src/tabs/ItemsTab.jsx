import { useState, useRef } from 'react'
import './ItemsTab.css'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { downloadBlob, detectBgColor } from '../utils'
import { X, Download, Grid, List, Eclipse, PaintBucket, ChevronDown, ChevronRight, Pencil } from 'lucide-react'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'

function GridIcon() { return <Grid size={12} fill="currentColor" /> }
function ListIcon()  { return <List size={12} fill="currentColor" /> }

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
// Inline bg color swatch + input
// ---------------------------------------------------------------------------
function BgColorCell({ color, onChange }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal]         = useState(color)

  const commit = () => {
    if (/^#[0-9a-fA-F]{6}$/.test(val)) onChange(val)
    else setVal(color)
    setEditing(false)
  }

  return (
    <div className="sprite-bg-cell" title="input bg — click to override">
      <div
        className="sprite-bg-swatch"
        style={{ background: color }}
        onClick={() => { setVal(color); setEditing(e => !e) }}
      />
      {editing && (
        <input
          className="sprite-bg-input"
          value={val}
          onChange={e => setVal(e.target.value)}
          onBlur={commit}
          onKeyDown={e => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') { setVal(color); setEditing(false) }
          }}
          maxLength={7}
          autoFocus
          spellCheck={false}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Item result card
// ---------------------------------------------------------------------------
function ItemCard({ result, isReference, listMode }) {
  return (
    <div className={`item-card ${isReference ? 'is-reference' : ''} ${listMode ? 'list-mode' : ''}`}>
      {listMode ? (
        <>
          <div className="item-card-preview">
            <ZoomableImage src={result.preview} alt={result.name} />
          </div>
          <div className="item-card-body">
            <div className="item-card-header">
              <span className="item-card-name">{result.name}</span>
              {isReference && <span className="item-card-ref-badge">ref</span>}
              <button
                className="sprite-queue-btn"
                onClick={() => downloadPal(result.pal_content, result.name)}
              >
                <Download size={11} />
              </button>
            </div>
            <PaletteStrip
              colors={result.colors}
              usedIndices={result.colors.map((_, i) => i)}
              checkSize="50%"
            />
          </div>
        </>
      ) : (
        <>
          <div className="item-card-header">
            <span className="item-card-name">{result.name}</span>
            {isReference && <span className="item-card-ref-badge">ref</span>}
          </div>
          <PaletteStrip
            colors={result.colors}
            usedIndices={result.colors.map((_, i) => i)}
            checkSize="100%"
          />
          <ZoomableImage src={result.preview} alt={result.name} />
          <button
            className="btn-secondary"
            onClick={() => downloadPal(result.pal_content, result.name)}
          >
            <Download size={11} /> download .pal
          </button>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Group section (collapsible)
// ---------------------------------------------------------------------------
function GroupSection({ group, groupName, onRename, viewMode, exact, nUnique }) {
  const [open, setOpen]       = useState(true)
  const [editing, setEditing] = useState(false)
  const [nameVal, setNameVal] = useState(groupName)

  const commitRename = () => {
    if (nameVal.trim()) onRename(nameVal.trim())
    else setNameVal(groupName)
    setEditing(false)
  }

  return (
    <div className="group-section">
      <div className="group-header">
        <button className="group-collapse-btn" onClick={() => setOpen(o => !o)}>
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>

        {editing ? (
          <input
            className="group-name-input"
            value={nameVal}
            onChange={e => setNameVal(e.target.value)}
            onBlur={commitRename}
            onKeyDown={e => {
              if (e.key === 'Enter') commitRename()
              if (e.key === 'Escape') { setNameVal(groupName); setEditing(false) }
            }}
            autoFocus
          />
        ) : (
          <span className="group-name" onClick={() => setEditing(true)}>
            {groupName}
          </span>
        )}

        <span className="group-meta">
          {group.dimensions} · {group.results.length} sprite{group.results.length !== 1 ? 's' : ''}
          {' · '}
          {exact
            ? <span style={{ color: 'var(--best)' }}>{nUnique} colors · exact</span>
            : <span style={{ color: '#e3b341' }}>{nUnique} → {group.results[0]?.colors.length - 1} colors · clustered</span>
          }
        </span>

        <button
          className="sprite-queue-btn"
          title="rename group"
          onClick={() => setEditing(true)}
        >
          <Pencil size={10} />
        </button>
      </div>

      {open && (
        <div className={viewMode === 'grid' ? 'items-results-grid' : 'items-results-list'}>
          {group.results.map(r => (
            <ItemCard
              key={r.name}
              result={r}
              isReference={r.name === group.reference}
              listMode={viewMode === 'list'}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main tab
// ---------------------------------------------------------------------------
export function ItemsTab() {
  const [sprites, setSprites]           = useState([])
  const [nColors, setNColors]           = useState(15)
  const [outputBg, setOutputBg]         = useState(GBA_TRANSPARENT)
  const [outputBgMode, setOutputBgMode] = useState('default')
  const [results, setResults]           = useState(null)
  const [groupNames, setGroupNames]     = useState({})
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [viewMode, setViewMode]         = useState('grid')
  const inputRef = useRef()

  const handleFiles = async (fileList) => {
    const incoming = Array.from(fileList)
    const loaded = await Promise.all(incoming.map(async f => {
      const b64     = await fileToB64(f)
      const inputBg = await detectBgColor(b64)
      return { file: f, name: f.name.replace(/\.[^.]+$/, ''), b64, inputBg }
    }))
    setSprites(prev => {
      const names = new Set(prev.map(s => s.name))
      return [...prev, ...loaded.filter(s => !names.has(s.name))]
    })
    setResults(null)
  }

  const updateInputBg = (idx, color) => {
    setSprites(prev => prev.map((s, i) => i === idx ? { ...s, inputBg: color } : s))
  }

  const removeSprite = (idx) => {
    setSprites(prev => prev.filter((_, i) => i !== idx))
    setResults(null)
  }

  const setAllInputBg = async (mode) => {
    if (mode === 'auto') {
      const detected = await Promise.all(sprites.map(s => detectBgColor(s.b64)))
      setSprites(prev => prev.map((s, i) => ({ ...s, inputBg: detected[i] })))
    } else if (mode === 'default') {
      setSprites(prev => prev.map(s => ({ ...s, inputBg: GBA_TRANSPARENT })))
    }
  }

  const handleExtract = async () => {
    if (sprites.length === 0) return
    setLoading(true); setError(null); setResults(null)
    try {
      const fd = new FormData()
      sprites.forEach(s => fd.append('files', s.file))
      fd.append('n_colors', nColors)
      fd.append('input_bg_colors', JSON.stringify(sprites.map(s => s.inputBg)))
      fd.append('output_bg_color', outputBg)
      const res = await fetch(`${API}/items/extract`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setResults(data)
      const names = {}
      data.groups.forEach(g => { names[g.group_id] = g.group_id })
      setGroupNames(names)
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
    fd.append('group_names', JSON.stringify(groupNames))
    const res = await fetch(`${API}/items/download-all`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), 'item_palettes.zip')
  }

  return (
    <div className="tab-content">
      <div className="items-layout">

        {/* ── Left ── */}
        <div className="items-left">

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
              <p className="dropzone-label">Drop sprites here</p>
              <p className="dropzone-hint">PNG · click or drag · multiple files</p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              multiple
              style={{ display: 'none' }}
              onChange={e => { if (e.target.files.length) handleFiles(e.target.files); e.target.value = '' }}
            />
          </div>

          {sprites.length > 0 && (
            <>
              <div className="sprite-queue">
                {sprites.map((s, i) => (
                  <div key={s.name} className="sprite-queue-row">
                    <img
                      src={`data:image/png;base64,${s.b64}`}
                      alt={s.name}
                      className="sprite-queue-thumb"
                    />
                    <span className="sprite-queue-name">{s.name}</span>
                    <BgColorCell
                      color={s.inputBg}
                      onChange={color => updateInputBg(i, color)}
                    />
                    <div className="sprite-queue-actions">
                      <button
                        className="sprite-queue-btn danger"
                        title="remove"
                        onClick={() => removeSprite(i)}
                      >
                        <X size={10} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="field">
                <label className="field-label">input bg — set all</label>
                <div className="bg-mode-row">
                  <button className="bg-mode-btn" onClick={() => setAllInputBg('auto')}>
                    re-detect all
                  </button>
                  <button className="bg-mode-btn" onClick={() => setAllInputBg('default')}>
                    set all #73C5A4
                  </button>
                </div>
              </div>
            </>
          )}

          <div className="field">
            <label className="field-label">output transparent (slot 0)</label>
            <div className="bg-mode-row">
              <button
                className={`bg-mode-btn ${outputBgMode === 'default' ? 'active' : ''}`}
                onClick={() => { setOutputBg(GBA_TRANSPARENT); setOutputBgMode('default') }}
              >default <Eclipse size={8} /></button>
              <button
                className={`bg-mode-btn ${outputBgMode === 'custom' ? 'active' : ''}`}
                onClick={() => setOutputBgMode('custom')}
              >custom <PaintBucket size={8} /></button>
            </div>
            <div className="bg-color-row">
              <div className="bg-swatch" style={{ background: outputBg }} />
              {outputBgMode === 'custom' ? (
                <input
                  className="field-input field-mono"
                  value={outputBg}
                  onChange={e => setOutputBg(e.target.value)}
                  maxLength={7}
                  placeholder="#73C5A4"
                />
              ) : (
                <span className="field-hint">
                  {outputBg} <span className="bg-mode-tag">GBA default</span>
                </span>
              )}
            </div>
          </div>

          <div className="field">
            <label className="field-label">colors per palette (max 15)</label>
            <input
              type="number"
              className="field-input"
              min={1} max={15}
              value={nColors}
              onChange={e => setNColors(Number(e.target.value))}
            />
          </div>

          <button
            className="btn-primary"
            disabled={sprites.length === 0 || loading}
            onClick={handleExtract}
          >
            {loading
              ? 'extracting…'
              : `extract ${sprites.length > 0 ? `${sprites.length} sprite${sprites.length > 1 ? 's' : ''}` : ''}`
            }
          </button>

          {results && (
            <button className="btn-secondary" onClick={handleDownloadAll}>
              <Download size={11} /> download all as zip
            </button>
          )}

          {error && <p className="error-msg">{error}</p>}
        </div>

        {/* ── Right ── */}
        <div className="items-right">
          <div className="items-toolbar">
            <span className="items-count">
              {results
                ? `${results.groups.length} group${results.groups.length !== 1 ? 's' : ''} · ${results.groups.reduce((n, g) => n + g.results.length, 0)} sprites`
                : ''
              }
            </span>
            {results && (
              <div className="view-toggle">
                <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')}><GridIcon /></button>
                <button className={`view-btn ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}><ListIcon /></button>
              </div>
            )}
          </div>

          {!results && !loading && (
            <div className="empty-state">
              <p>drop sprites — they'll be auto-grouped by silhouette</p>
            </div>
          )}
          {loading && (
            <div className="empty-state"><div className="spinner" /><p>grouping and extracting…</p></div>
          )}

          {results && (
            <div className="groups-list">
              {results.groups.map(group => (
                <GroupSection
                  key={group.group_id}
                  group={group}
                  groupName={groupNames[group.group_id] ?? group.group_id}
                  onRename={name => setGroupNames(prev => ({ ...prev, [group.group_id]: name }))}
                  viewMode={viewMode}
                  exact={group.exact}
                  nUnique={group.n_unique}
                />
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}