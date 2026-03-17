import { useState, useRef, useCallback, useEffect } from 'react'
import './ItemsTab.css'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { downloadBlob, detectBgColor } from '../utils'
import {
  X, Download, Grid, List, Eclipse, PaintBucket,
  ChevronDown, ChevronRight, Pencil, GripVertical, Merge
} from 'lucide-react'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'
const AUTO_EXTRACT_DELAY_MS = 900

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
// BgColorCell
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
      <div className="sprite-bg-swatch" style={{ background: color }}
        onClick={() => { setVal(color); setEditing(e => !e) }} />
      {editing && (
        <input className="sprite-bg-input" value={val}
          onChange={e => setVal(e.target.value)} onBlur={commit}
          onKeyDown={e => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') { setVal(color); setEditing(false) }
          }}
          maxLength={7} autoFocus spellCheck={false} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ThresholdSlider
// ---------------------------------------------------------------------------
function ThresholdSlider({ value, onChange }) {
  const pct   = Math.round(value * 100)
  const label = value <= 0.1 ? 'any shared' : value <= 0.4 ? 'loose' :
                value <= 0.6 ? 'majority'   : value <= 0.85 ? 'strict' : 'all sprites'
  return (
    <div className="field">
      <div className="threshold-header">
        <label className="field-label">shared color threshold</label>
        <span className="threshold-value">{pct}% · {label}</span>
      </div>
      <input type="range" className="threshold-slider" min={0} max={100} step={5}
        value={pct} onChange={e => onChange(Number(e.target.value) / 100)} />
      <p className="threshold-hint">
        A color must appear in ≥{pct}% of a group to earn a fixed shared slot.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// MergeDropdown — lists other groups to merge this whole group into
// ---------------------------------------------------------------------------
function MergeDropdown({ thisGroupId, allGroups, groupNames, onMerge }) {
  const [open, setOpen] = useState(false)
  const ref = useRef()

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const others = allGroups.filter(g => g.group_id !== thisGroupId)
  if (others.length === 0) return null

  return (
    <div className="merge-dropdown" ref={ref}>
      <button
        className="group-action-btn"
        title="merge entire group into another"
        onClick={e => { e.stopPropagation(); setOpen(o => !o) }}
      >
        <Merge size={11} />
      </button>
      {open && (
        <div className="merge-menu">
          <p className="merge-menu-label">merge into…</p>
          {others.map(g => (
            <button key={g.group_id} className="merge-menu-item"
              onClick={e => { e.stopPropagation(); setOpen(false); onMerge(thisGroupId, g.group_id) }}>
              {groupNames[g.group_id] ?? g.group_id}
              <span className="merge-menu-meta">{g.results.length} sprites</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ItemCard — draggable
// ---------------------------------------------------------------------------
function ItemCard({ result, isReference, listMode, groupId }) {
  const handleDragStart = (e) => {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ spriteName: result.name, fromGroupId: groupId }))
  }

  return (
    <div
      className={`item-card ${isReference ? 'is-reference' : ''} ${listMode ? 'list-mode' : ''}`}
      draggable
      onDragStart={handleDragStart}
    >
      <div className="item-drag-handle" title="drag to move to another group">
        <GripVertical size={12} />
      </div>

      {listMode ? (
        <>
          <div className="item-card-preview">
            <ZoomableImage src={result.preview} alt={result.name} />
          </div>
          <div className="item-card-body">
            <div className="item-card-header">
              <span className="item-card-name">{result.name}</span>
              {isReference && <span className="item-card-ref-badge">ref</span>}
              <button className="sprite-queue-btn"
                onClick={() => downloadPal(result.pal_content, result.name)}>
                <Download size={11} />
              </button>
            </div>
            <PaletteStrip colors={result.colors} usedIndices={result.colors.map((_, i) => i)} checkSize="50%" />
          </div>
        </>
      ) : (
        <>
          <div className="item-card-header">
            <span className="item-card-name">{result.name}</span>
            {isReference && <span className="item-card-ref-badge">ref</span>}
          </div>
          <PaletteStrip colors={result.colors} usedIndices={result.colors.map((_, i) => i)} checkSize="100%" />
          <ZoomableImage src={result.preview} alt={result.name} />
          <button className="btn-secondary" onClick={() => downloadPal(result.pal_content, result.name)}>
            <Download size={11} /> download .pal
          </button>
        </>
      )}
    </div>
  )
}


// ---------------------------------------------------------------------------
// SharedSlotsStrip — shows all palette slots for a group, marking shared vs local
// ---------------------------------------------------------------------------
function SharedSlotsStrip({ sharedSlots, nShared }) {
  const [hoveredIdx, setHoveredIdx] = useState(null)

  if (!sharedSlots || sharedSlots.length === 0) return null

  return (
    <div className="shared-slots-wrap">
      <div className="shared-slots-header">
        <span className="shared-slots-label">shared indices</span>
        <span className="shared-slots-count">
          {nShared + 1} shared (0–{nShared}) · {sharedSlots.length - nShared - 1} local
        </span>
      </div>
      <div className="shared-slots-strip">
        {sharedSlots.map((slot, i) => (
          <div
            key={i}
            className={`shared-slot ${slot.shared ? 'is-shared' : 'is-local'}`}
            style={{ background: slot.hex }}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            {hoveredIdx === i && (
              <div className="shared-slot-tooltip">
                <span className="shared-slot-idx">{i}</span>
                <span className="shared-slot-hex">{slot.hex}</span>
                <span className={`shared-slot-tag ${slot.shared ? 'tag-shared' : 'tag-local'}`}>
                  {slot.shared ? 'shared' : 'local'}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
      {/* Shared indicator bar below the strip */}
      <div className="shared-slots-bar">
        {sharedSlots.map((slot, i) => (
          <div key={i} className={`shared-bar-tick ${slot.shared ? 'tick-shared' : 'tick-local'}`} />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// GroupSection
// ---------------------------------------------------------------------------
function GroupSection({
  group, groupName, onRename, onDropSprite, onMergeGroup,
  allGroups, groupNames,
  viewMode, exact, nUnique,
  sharedSlots, nShared,
}) {
  const [open, setOpen]         = useState(true)
  const [editing, setEditing]   = useState(false)
  const [nameVal, setNameVal]   = useState(groupName)
  const [dragOver, setDragOver] = useState(false)

  // Keep nameVal in sync if groupName changes externally
  useEffect(() => { setNameVal(groupName) }, [groupName])

  const commitRename = () => {
    if (nameVal.trim()) onRename(nameVal.trim())
    else setNameVal(groupName)
    setEditing(false)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(true)
  }
  const handleDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragOver(false)
  }
  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (data.fromGroupId !== group.group_id) {
        onDropSprite(data.spriteName, data.fromGroupId, group.group_id)
      }
    } catch { /* ignore */ }
  }

  return (
    <div className={`group-section ${dragOver ? 'group-drop-target' : ''}`}>
      <div className="group-header"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <button className="group-collapse-btn" onClick={() => setOpen(o => !o)}>
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>

        {editing ? (
          <input className="group-name-input" value={nameVal}
            onChange={e => setNameVal(e.target.value)} onBlur={commitRename}
            onKeyDown={e => {
              if (e.key === 'Enter') commitRename()
              if (e.key === 'Escape') { setNameVal(groupName); setEditing(false) }
            }} autoFocus />
        ) : (
          <span className="group-name" onClick={() => setEditing(true)}>{groupName}</span>
        )}

        <span className="group-meta">
          {group.dimensions} · {group.results.length} sprite{group.results.length !== 1 ? 's' : ''}
          {' · '}
          {exact
            ? <span style={{ color: 'var(--best)' }}>{nUnique} colors · exact</span>
            : <span style={{ color: '#e3b341' }}>{nUnique} → {group.results[0]?.colors.length - 1} colors · clustered</span>
          }
        </span>

        {/* Actions row */}
        <div className="group-actions">
          {/* Rename */}
          <button className="group-action-btn" title="rename" onClick={() => setEditing(true)}>
            <Pencil size={11} />
          </button>

          {/* Merge into another group */}
          <MergeDropdown
            thisGroupId={group.group_id}
            allGroups={allGroups}
            groupNames={groupNames}
            onMerge={onMergeGroup}
          />
        </div>

        {dragOver && <span className="group-drop-hint">drop to merge</span>}
      </div>

      {open && sharedSlots && sharedSlots.length > 0 && (
        <SharedSlotsStrip sharedSlots={sharedSlots} nShared={nShared ?? 0} />
      )}

      {open && (
        <div className={viewMode === 'grid' ? 'items-results-grid' : 'items-results-list'}>
          {group.results.map(r => (
            <ItemCard
              key={r.name}
              result={r}
              isReference={r.name === group.reference}
              listMode={viewMode === 'list'}
              groupId={group.group_id}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Tab
// ---------------------------------------------------------------------------
export function ItemsTab() {
  const [sprites, setSprites]                   = useState([])
  const [nColors, setNColors]                   = useState(15)
  const [outputBg, setOutputBg]                 = useState(GBA_TRANSPARENT)
  const [outputBgMode, setOutputBgMode]         = useState('default')
  const [sharedThreshold, setSharedThreshold]   = useState(0.6)
  const [results, setResults]                   = useState(null)
  const [groupNames, setGroupNames]             = useState({})
  // groupAssignments: spriteName -> groupId (manual overrides, used on re-extract)
  const [groupAssignments, setGroupAssignments] = useState({})
  const [loading, setLoading]                   = useState(false)
  const [error, setError]                       = useState(null)
  const [viewMode, setViewMode]                 = useState('grid')
  const [groupingEnabled, setGroupingEnabled]   = useState(true)

  const inputRef        = useRef()
  const autoExtractTimer = useRef(null)
// ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  // Build group_assignments from the current displayed groups
  const buildAssignments = useCallback((displayedGroups) => {
    const assignments = {}
    displayedGroups.forEach(group => {
      group.results.forEach(r => {
        assignments[r.name] = group.group_id
      })
    })
    return assignments
  }, [])

  // ---------------------------------------------------------------------------
  // Extract
  // ---------------------------------------------------------------------------
  const doExtract = useCallback(async (displayedGroups, currentGrouping) => {
    if (sprites.length === 0) return
    setLoading(true)
    setError(null)

    // When grouping is disabled, give every sprite a unique solo key
    const assignments = currentGrouping
      ? buildAssignments(displayedGroups)
      : Object.fromEntries(sprites.map(s => [s.name, `solo_${s.name}`]))
    setGroupAssignments(assignments)

    try {
      const fd = new FormData()
      sprites.forEach(s => fd.append('files', s.file))
      fd.append('n_colors', nColors)
      fd.append('input_bg_colors', JSON.stringify(sprites.map(s => s.inputBg)))
      fd.append('output_bg_color', outputBg)
      fd.append('shared_threshold', sharedThreshold)
      fd.append('group_assignments', JSON.stringify(assignments))

      const res = await fetch(`${API}/items/extract`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()

      setResults(data)

      // Carry over group names for groups that still exist
      setGroupNames(prev => {
        const next = {}
        data.groups.forEach(g => {
          next[g.group_id] = prev[g.group_id] ?? g.group_id
        })
        return next
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [sprites, nColors, outputBg, sharedThreshold, buildAssignments])

  // Initial extract (no prior groups)
  const handleExtract = () => {
    clearTimeout(autoExtractTimer.current)
    doExtract([], groupingEnabled)
    setGroupAssignments({})
  }

  // ---------------------------------------------------------------------------
  // Auto-extract after group edits (debounced)
  // ---------------------------------------------------------------------------
  const scheduleAutoExtract = useCallback((newGroups) => {
    clearTimeout(autoExtractTimer.current)
    autoExtractTimer.current = setTimeout(() => {
      doExtract(newGroups, groupingEnabled)
    }, AUTO_EXTRACT_DELAY_MS)
  }, [doExtract, groupingEnabled])

  // ---------------------------------------------------------------------------
  // File import — sorted alphabetically
  // ---------------------------------------------------------------------------
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
      const names = new Set(prev.map(s => s.name))
      // Merge new sorted sprites, then re-sort the full list
      const merged = [...prev, ...loaded.filter(s => !names.has(s.name))]
      return merged.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
    })
    setResults(null)
    setGroupAssignments({})
  }

  const updateInputBg = (idx, color) =>
    setSprites(prev => prev.map((s, i) => i === idx ? { ...s, inputBg: color } : s))

  const removeSprite = (idx) => {
    setSprites(prev => prev.filter((_, i) => i !== idx))
    setResults(null)
  }

  const setAllInputBg = async (mode) => {
    if (mode === 'auto') {
      const detected = await Promise.all(sprites.map(s => detectBgColor(s.b64)))
      setSprites(prev => prev.map((s, i) => ({ ...s, inputBg: detected[i] })))
    } else {
      setSprites(prev => prev.map(s => ({ ...s, inputBg: GBA_TRANSPARENT })))
    }
  }

  // ---------------------------------------------------------------------------
  // Group editing operations — all trigger auto-extract
  // ---------------------------------------------------------------------------

  // Move a single sprite card from one group to another
  const handleDropSprite = useCallback((spriteName, fromGroupId, toGroupId) => {
    setResults(prev => {
      if (!prev) return prev
      const fromGroup = prev.groups.find(g => g.group_id === fromGroupId)
      const toGroup   = prev.groups.find(g => g.group_id === toGroupId)
      if (!fromGroup || !toGroup) return prev

      const moved = fromGroup.results.find(r => r.name === spriteName)
      if (!moved) return prev

      const newGroups = prev.groups.map(g => {
        if (g.group_id === fromGroupId) return { ...g, results: g.results.filter(r => r.name !== spriteName) }
        if (g.group_id === toGroupId)   return { ...g, results: [...g.results, moved] }
        return g
      }).filter(g => g.results.length > 0)

      scheduleAutoExtract(newGroups)
      return { ...prev, groups: newGroups }
    })
  }, [scheduleAutoExtract])

  // Merge ALL sprites from fromGroupId into toGroupId
  const handleMergeGroup = useCallback((fromGroupId, toGroupId) => {
    setResults(prev => {
      if (!prev) return prev

      const fromGroup = prev.groups.find(g => g.group_id === fromGroupId)
      const toGroup   = prev.groups.find(g => g.group_id === toGroupId)
      if (!fromGroup || !toGroup) return prev

      const newGroups = prev.groups.map(g => {
        if (g.group_id === toGroupId) return { ...g, results: [...g.results, ...fromGroup.results] }
        return g
      }).filter(g => g.group_id !== fromGroupId)

      scheduleAutoExtract(newGroups)
      return { ...prev, groups: newGroups }
    })
  }, [scheduleAutoExtract])

  // ---------------------------------------------------------------------------
  // Download
  // ---------------------------------------------------------------------------
  const handleDownloadAll = async () => {
    const currentGroups = results?.groups ?? []
    const assignments   = groupingEnabled ? buildAssignments(currentGroups) : Object.fromEntries(sprites.map(s => [s.name, `solo_${s.name}`]))

    const fd = new FormData()
    sprites.forEach(s => fd.append('files', s.file))
    fd.append('n_colors', nColors)
    fd.append('input_bg_colors', JSON.stringify(sprites.map(s => s.inputBg)))
    fd.append('output_bg_color', outputBg)
    fd.append('shared_threshold', sharedThreshold)
    fd.append('group_assignments', JSON.stringify(assignments))
    fd.append('group_names', JSON.stringify(groupNames))
    const res = await fetch(`${API}/items/download-all`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), 'item_palettes.zip')
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
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
              <p className="dropzone-hint">PNG, JPG, BMP · click or drag</p>
            </div>
            <input ref={inputRef} type="file" accept="image/*" multiple style={{ display: 'none' }}
              onChange={e => { if (e.target.files.length) handleFiles(e.target.files); e.target.value = '' }} />
          </div>

          {sprites.length > 0 && (
            <>
              <div className="sprite-queue">
                {sprites.map((s, i) => (
                  <div key={s.name} className="sprite-queue-row">
                    <img src={`data:image/png;base64,${s.b64}`} alt={s.name} className="sprite-queue-thumb" />
                    <span className="sprite-queue-name">{s.name}</span>
                    <BgColorCell color={s.inputBg} onChange={color => updateInputBg(i, color)} />
                    <div className="sprite-queue-actions">
                      <button className="sprite-queue-btn danger" title="remove" onClick={() => removeSprite(i)}>
                        <X size={10} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="field">
                <label className="field-label">input bg — set all</label>
                <div className="bg-mode-row">
                  <button className="bg-mode-btn" onClick={() => setAllInputBg('auto')}>re-detect all</button>
                  <button className="bg-mode-btn" onClick={() => setAllInputBg('default')}>set all #73C5A4</button>
                </div>
              </div>
            </>
          )}

          <div className="field">
            <label className="field-label">output transparent (slot 0)</label>
            <div className="bg-mode-row">
              <button className={`bg-mode-btn ${outputBgMode === 'default' ? 'active' : ''}`}
                onClick={() => { setOutputBg(GBA_TRANSPARENT); setOutputBgMode('default') }}>
                default <Eclipse size={8} /></button>
              <button className={`bg-mode-btn ${outputBgMode === 'custom' ? 'active' : ''}`}
                onClick={() => setOutputBgMode('custom')}>
                custom <PaintBucket size={8} /></button>
            </div>
            <div className="bg-color-row">
              <div className="bg-swatch" style={{ background: outputBg }} />
              {outputBgMode === 'custom'
                ? <input className="field-input field-mono" value={outputBg}
                    onChange={e => setOutputBg(e.target.value)} maxLength={7} placeholder="#73C5A4" />
                : <span className="field-hint">{outputBg} <span className="bg-mode-tag">GBA default</span></span>
              }
            </div>
          </div>

          <div className="field">
            <label className="field-label">colors per palette (max 15)</label>
            <input type="number" className="field-input" min={1} max={15} value={nColors}
              onChange={e => setNColors(Number(e.target.value))} />
          </div>

          {/* Grouping toggle */}
          <div className="grouping-toggle-row">
            <span className="field-label">group by silhouette</span>
            <button
              className={`grouping-toggle-btn ${groupingEnabled ? 'on' : 'off'}`}
              onClick={() => {
                const next = !groupingEnabled
                setGroupingEnabled(next)
                // Re-extract immediately with new grouping mode using current groups
                clearTimeout(autoExtractTimer.current)
                if (results) doExtract(results.groups, next)
              }}
            >
              {groupingEnabled ? 'on' : 'off'}
            </button>
          </div>

          {groupingEnabled && <ThresholdSlider value={sharedThreshold} onChange={setSharedThreshold} />}

          <button className="btn-primary" disabled={sprites.length === 0 || loading}
            onClick={handleExtract}>
            {loading ? 'extracting…' : `extract ${sprites.length > 0 ? `${sprites.length} sprite${sprites.length > 1 ? 's' : ''}` : ''}`}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {loading && <span className="auto-extract-indicator">re-extracting…</span>}
                <div className="view-toggle">
                  <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')}><GridIcon /></button>
                  <button className={`view-btn ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}><ListIcon /></button>
                </div>
              </div>
            )}
          </div>

          {!results && !loading && (
            <div className="empty-state">
              <p>drop sprites — auto-grouped by silhouette</p>
              <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
                drag cards or use merge/unlink buttons to reorganise · re-extracts automatically
              </p>
            </div>
          )}
          {loading && !results && <div className="empty-state"><div className="spinner" /><p>grouping and extracting…</p></div>}

          {results && (
            <div className="groups-list">
              {results.groups.map(group => (
                <GroupSection
                  key={group.group_id}
                  group={group}
                  groupName={groupNames[group.group_id] ?? group.group_id}
                  onRename={name => setGroupNames(prev => ({ ...prev, [group.group_id]: name }))}
                  onDropSprite={handleDropSprite}
                  onMergeGroup={handleMergeGroup}
                  allGroups={results.groups}
                  groupNames={groupNames}
                  viewMode={viewMode}
                  exact={group.exact}
                  nUnique={group.n_unique}
                  sharedSlots={group.shared_slots}
                  nShared={group.n_shared}
                />
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}