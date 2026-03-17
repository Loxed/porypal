import { useState, useRef, useCallback } from 'react'
import './ItemsTab.css'
import { BgColorCell } from '../components/BgColorCell'
import { GroupSection } from '../components/GroupSection'
import { VariantsPanel } from '../components/VariantsPanel'
import { downloadBlob, detectBgColor } from '../utils'
import { X, Download, Grid, List, Eclipse, PaintBucket } from 'lucide-react'

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

// ---------------------------------------------------------------------------
// ThresholdSlider — items-specific, stays in tab
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
// ItemsTab
// ---------------------------------------------------------------------------
export function ItemsTab() {
  const [mode, setMode]                         = useState('group') // 'group' | 'variants'
  const [sprites, setSprites]                   = useState([])
  const [nColors, setNColors]                   = useState(15)
  const [outputBg, setOutputBg]                 = useState(GBA_TRANSPARENT)
  const [outputBgMode, setOutputBgMode]         = useState('default')
  const [sharedThreshold, setSharedThreshold]   = useState(0.6)
  const [groupingEnabled, setGroupingEnabled]   = useState(true)
  const [results, setResults]                   = useState(null)
  const [groupNames, setGroupNames]             = useState({})
  const [groupAssignments, setGroupAssignments] = useState({})
  const [loading, setLoading]                   = useState(false)
  const [error, setError]                       = useState(null)
  const [viewMode, setViewMode]                 = useState('grid')

  const inputRef         = useRef()
  const autoExtractTimer = useRef(null)

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  const buildAssignments = useCallback((displayedGroups) => {
    const assignments = {}
    displayedGroups.forEach(group => {
      group.results.forEach(r => { assignments[r.name] = group.group_id })
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

    const assignments = currentGrouping
      ? buildAssignments(displayedGroups)
      : Object.fromEntries(sprites.map(s => [s.name, 'all']))
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
      setGroupNames(prev => {
        const next = {}
        data.groups.forEach(g => { next[g.group_id] = prev[g.group_id] ?? g.group_id })
        return next
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [sprites, nColors, outputBg, sharedThreshold, buildAssignments])

  const handleExtract = () => {
    clearTimeout(autoExtractTimer.current)
    doExtract([], groupingEnabled)
    setGroupAssignments({})
  }

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
      const names  = new Set(prev.map(s => s.name))
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
  // Group editing — all trigger auto-extract
  // ---------------------------------------------------------------------------
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

  const handleMergeGroup = useCallback((fromGroupId, toGroupId) => {
    setResults(prev => {
      if (!prev) return prev
      const fromGroup = prev.groups.find(g => g.group_id === fromGroupId)
      if (!fromGroup) return prev
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
    const assignments   = groupingEnabled
      ? buildAssignments(currentGroups)
      : Object.fromEntries(sprites.map(s => [s.name, 'all']))

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
      {/* ── Mode switcher ── */}
      <div className="items-mode-switcher">
        <button
          className={`items-mode-btn ${mode === 'group' ? 'active' : ''}`}
          onClick={() => setMode('group')}
        >
          extract groups 
        </button>
        <button
          className={`items-mode-btn ${mode === 'variants' ? 'active' : ''}`}
          onClick={() => setMode('variants')}
        >
          item variants
        </button>
      </div>

      {mode === 'variants' && (
        <VariantsPanel
          nColors={nColors}
          outputBg={outputBg}
          outputBgMode={outputBgMode}
          setOutputBg={setOutputBg}
          setOutputBgMode={setOutputBgMode}
        />
      )}

      {mode === 'group' && (
        <div className="items-layout">
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
              <p className="dropzone-hint">PNG · click or drag · sorted A–Z</p>
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

          <div className="grouping-toggle-row">
            <span className="field-label">group by silhouette</span>
            <button
              className={`grouping-toggle-btn ${groupingEnabled ? 'on' : 'off'}`}
              onClick={() => {
                const next = !groupingEnabled
                setGroupingEnabled(next)
                clearTimeout(autoExtractTimer.current)
                if (results) doExtract(results.groups, next)
              }}
            >
              {groupingEnabled ? 'on' : 'off'}
            </button>
          </div>

          <ThresholdSlider value={sharedThreshold} onChange={setSharedThreshold} />

          <button className="btn-primary" disabled={sprites.length === 0 || loading} onClick={handleExtract}>
            {loading ? 'extracting…' : `extract ${sprites.length > 0 ? `${sprites.length} sprite${sprites.length > 1 ? 's' : ''}` : ''}`}
          </button>

          {results && (
            <button className="btn-secondary" onClick={handleDownloadAll}>
              <Download size={11} /> download all as zip
            </button>
          )}

          {error && <p className="error-msg">{error}</p>}
        </div>

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
                drag cards or use merge button to reorganise · re-extracts automatically
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
      )}

    </div>
  )
}