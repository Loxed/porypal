import { useState, useEffect, useRef } from 'react'
import './BatchTab.css'
import { useFetch } from '../hooks/useFetch'
import { Trash2, ChevronUp, ChevronDown, Play, Download, X, AlertTriangle, Check, Loader } from 'lucide-react'

const API = '/api'

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------
const STEP_DEFAULTS = {
  extract: {
    n_colors: 15,
    color_space: 'oklab',
    bg_mode: 'auto',
    bg_color: '#73C5A4',
    save_palette: true,
  },
  tileset: {
    preset_id: '',
  },
  convert: {
    palette_source: 'loaded',
    selected_palettes: [],
    conflict_mode: 'auto_first',
  },
}

const STEP_LABELS = { extract: 'Extract Palette', tileset: 'Apply Preset', convert: 'Apply Palette' }
const STEP_COLORS = { extract: 'step--extract', tileset: 'step--tileset', convert: 'step--convert' }

let _stepCounter = 0
const makeStep = (type) => ({ id: `step_${++_stepCounter}`, type, config: { ...STEP_DEFAULTS[type] } })

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------
function validateStep(step, index, allSteps) {
  if (step.type === 'tileset' && !step.config.preset_id)
    return 'Select a preset'
  if (step.type === 'convert') {
    if (step.config.palette_source === 'loaded' && step.config.selected_palettes.length === 0)
      return 'Select at least one palette'
    if (step.config.palette_source === 'extracted') {
      const hasExtractBefore = allSteps.slice(0, index).some(s => s.type === 'extract')
      if (!hasExtractBefore) return 'No Extract step before this Convert step'
    }
  }
  return null
}

// ---------------------------------------------------------------------------
// Step config sub-forms
// ---------------------------------------------------------------------------
function ExtractConfig({ config, onChange }) {
  const set = (k, v) => onChange({ ...config, [k]: v })
  return (
    <div className="step-config">
      <div className="step-config-row">
        <label className="step-config-label">colors</label>
        <input type="number" min={1} max={15} className="step-input-num" value={config.n_colors}
          onChange={e => set('n_colors', Number(e.target.value))} />
        <span className="step-config-hint">max 15 (+ transparent)</span>
      </div>
      <div className="step-config-row">
        <label className="step-config-label">color space</label>
        <div className="step-toggle-row">
          {['oklab', 'rgb'].map(s => (
            <button key={s} className={`step-toggle ${config.color_space === s ? 'active' : ''}`}
              onClick={() => set('color_space', s)}>{s}</button>
          ))}
        </div>
      </div>
      <div className="step-config-row">
        <label className="step-config-label">bg color</label>
        <div className="step-toggle-row">
          {['auto', 'default', 'fixed'].map(m => (
            <button key={m} className={`step-toggle ${config.bg_mode === m ? 'active' : ''}`}
              onClick={() => set('bg_mode', m)}>{m}</button>
          ))}
        </div>
        {config.bg_mode === 'fixed' && (
          <input className="step-input-hex" value={config.bg_color} maxLength={7}
            onChange={e => set('bg_color', e.target.value)} placeholder="#73C5A4" />
        )}
      </div>
      <div className="step-config-row">
        <label className="step-config-label">save palette</label>
        <label className="step-checkbox">
          <input type="checkbox" checked={config.save_palette}
            onChange={e => set('save_palette', e.target.checked)} />
          save to palettes/user/
        </label>
      </div>
    </div>
  )
}

function TilesetConfig({ config, onChange, presets }) {
  const set = (k, v) => onChange({ ...config, [k]: v })
  return (
    <div className="step-config">
      <div className="step-config-row">
        <label className="step-config-label">preset</label>
        <select className="step-select" value={config.preset_id}
          onChange={e => set('preset_id', e.target.value)}>
          <option value="">select preset…</option>
          {presets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      {config.preset_id && (
        <div className="step-config-hint-block">
          {(() => { const p = presets.find(x => x.id === config.preset_id); return p ? `${p.cols}×${p.rows} grid · ${p.tile_w}px tiles` : '' })()}
        </div>
      )}
    </div>
  )
}

function ConvertConfig({ config, onChange, palettes, hasExtractBefore }) {
  const set = (k, v) => onChange({ ...config, [k]: v })
  const togglePalette = (name) => {
    const sel = config.selected_palettes.includes(name)
      ? config.selected_palettes.filter(n => n !== name)
      : [...config.selected_palettes, name]
    set('selected_palettes', sel)
  }
  return (
    <div className="step-config">
      <div className="step-config-row">
        <label className="step-config-label">palette source</label>
        <div className="step-toggle-row">
          <button className={`step-toggle ${config.palette_source === 'loaded' ? 'active' : ''}`}
            onClick={() => set('palette_source', 'loaded')}>loaded palettes</button>
          <button
            className={`step-toggle ${config.palette_source === 'extracted' ? 'active' : ''} ${!hasExtractBefore ? 'disabled' : ''}`}
            onClick={() => hasExtractBefore && set('palette_source', 'extracted')}
            title={!hasExtractBefore ? 'Add an Extract step before this one' : ''}>
            from extract step
          </button>
        </div>
      </div>
      {config.palette_source === 'loaded' && (
        <div className="step-config-row step-config-row--col">
          <label className="step-config-label">palettes</label>
          {palettes.length === 0
            ? <span className="step-config-hint">No palettes loaded</span>
            : (
              <div className="step-palette-list">
                {palettes.map(p => (
                  <label key={p.name} className="step-pal-check">
                    <input type="checkbox" checked={config.selected_palettes.includes(p.name)}
                      onChange={() => togglePalette(p.name)} />
                    <span>{p.name.replace('.pal', '')}</span>
                  </label>
                ))}
              </div>
            )
          }
        </div>
      )}
      <div className="step-config-row">
        <label className="step-config-label">on tie</label>
        <div className="step-toggle-row">
          <button className={`step-toggle ${config.conflict_mode === 'auto_first' ? 'active' : ''}`}
            onClick={() => set('conflict_mode', 'auto_first')} title="Automatically pick first alphabetically">
            auto-resolve
          </button>
          <button className={`step-toggle ${config.conflict_mode === 'flag' ? 'active' : ''}`}
            onClick={() => set('conflict_mode', 'flag')} title="Mark as conflict in summary">
            flag conflict
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step card
// ---------------------------------------------------------------------------
function StepCard({ step, index, total, allSteps, onChange, onMove, onDelete, palettes, presets }) {
  const [expanded, setExpanded] = useState(true)
  const error = validateStep(step, index, allSteps)
  const hasExtractBefore = allSteps.slice(0, index).some(s => s.type === 'extract')

  return (
    <div className={`step-card ${STEP_COLORS[step.type]} ${error ? 'step-card--error' : ''}`}>
      <div className="step-card-header">
        <div className="step-reorder">
          <button className="step-reorder-btn" onClick={() => onMove(index, -1)} disabled={index === 0}><ChevronUp size={11}/></button>
          <button className="step-reorder-btn" onClick={() => onMove(index, 1)} disabled={index === total - 1}><ChevronDown size={11}/></button>
        </div>
        <span className="step-num">{index + 1}</span>
        <span className={`step-badge ${STEP_COLORS[step.type]}`}>{step.type}</span>
        <span className="step-title">{STEP_LABELS[step.type]}</span>
        {error && <span className="step-error-hint"><AlertTriangle size={11}/> {error}</span>}
        <button className="step-expand-btn" onClick={() => setExpanded(e => !e)}>
          {expanded ? 'hide' : 'config'}
        </button>
        <button className="step-delete-btn" onClick={() => onDelete(index)}>
          <X size={12}/>
        </button>
      </div>
      {expanded && (
        <div className="step-card-body">
          {step.type === 'extract' && <ExtractConfig config={step.config} onChange={c => onChange(index, c)} />}
          {step.type === 'tileset' && <TilesetConfig config={step.config} onChange={c => onChange(index, c)} presets={presets} />}
          {step.type === 'convert' && (
            <ConvertConfig config={step.config} onChange={c => onChange(index, c)}
              palettes={palettes} hasExtractBefore={hasExtractBefore} />
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Progress panel
// ---------------------------------------------------------------------------
function ProgressPanel({ status, jobId, onReset }) {
  const pct = status.total > 0 ? Math.round((status.done / status.total) * 100) : 0
  const ok        = status.results.filter(r => r.status === 'ok').length
  const conflicts = status.results.filter(r => r.status === 'conflict').length
  const errors    = status.results.filter(r => r.status === 'error').length
  const isDone    = status.status === 'done'

  return (
    <div className="progress-panel">
      <div className="progress-header">
        <span className="section-label">
          {isDone ? 'done' : `processing — ${status.done} / ${status.total}`}
        </span>
        {isDone && (
          <div className="progress-header-actions">
            <button className="btn-primary-sm" onClick={() => { window.location.href = `${API}/pipeline/download/${jobId}` }}>
              <Download size={12}/> download results.zip
            </button>
            <button className="progress-reset-btn" onClick={onReset} title="new job">
              <X size={12}/>
            </button>
          </div>
        )}
      </div>
      <div className="progress-bar-wrap">
        <div className="progress-bar" style={{ width: `${pct}%` }} />
      </div>
      {!isDone && status.current_file && (
        <p className="progress-current">⌛ {status.current_file}</p>
      )}
      {isDone && (
        <div className="progress-stats">
          <span className="progress-stat stat--ok"><Check size={11}/> {ok} ok</span>
          {conflicts > 0 && <span className="progress-stat stat--conflict"><AlertTriangle size={11}/> {conflicts} conflict</span>}
          {errors    > 0 && <span className="progress-stat stat--error"><X size={11}/> {errors} error</span>}
        </div>
      )}
      {status.results.length > 0 && (
        <div className="progress-results">
          {status.results.map((r, i) => (
            <div key={i} className={`progress-result-row status--${r.status}`}>
              <span className="pres-icon">
                {r.status === 'ok'       && <Check size={11}/>}
                {r.status === 'conflict' && <AlertTriangle size={11}/>}
                {r.status === 'error'    && <X size={11}/>}
              </span>
              <span className="pres-file">{r.file}</span>
              {r.notes && <span className="pres-notes">{r.notes}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main tab
// ---------------------------------------------------------------------------
export function BatchTab() {
  const [files, setFiles]       = useState([])
  const [dragging, setDragging] = useState(false)
  const [steps, setSteps]       = useState([])
  const [palettes, setPalettes] = useState([])
  const [presets, setPresets]   = useState([])

  const [jobId, setJobId]         = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [running, setRunning]     = useState(false)
  const [runError, setRunError]   = useState(null)

  const fileInputRef   = useRef()  // individual files
  const folderInputRef = useRef()  // whole folder
  const pollRef        = useRef(null)

  useEffect(() => {
    fetch(`${API}/palettes`).then(r => r.json()).then(setPalettes).catch(() => {})
    fetch(`${API}/presets`).then(r => r.json()).then(setPresets).catch(() => {})
  }, [])

  useEffect(() => {
    if (!jobId || !running) return
    pollRef.current = setInterval(async () => {
      try {
        const s = await fetch(`${API}/pipeline/status/${jobId}`).then(r => r.json())
        setJobStatus(s)
        if (s.status === 'done' || s.status === 'error') {
          setRunning(false)
          clearInterval(pollRef.current)
        }
      } catch { /* ignore */ }
    }, 700)
    return () => clearInterval(pollRef.current)
  }, [jobId, running])

  const handleFiles = (fileList) => {
    const picked = Array.from(fileList).filter(f =>
      /\.(png|jpg|jpeg|bmp|gif)$/i.test(f.name)
    )
    setFiles(picked)
    setJobId(null); setJobStatus(null); setRunError(null)
  }

  const addStep = (type) => setSteps(prev => [...prev, makeStep(type)])

  const updateStepConfig = (index, newConfig) => {
    setSteps(prev => prev.map((s, i) => i === index ? { ...s, config: newConfig } : s))
  }

  const moveStep = (index, dir) => {
    setSteps(prev => {
      const next = [...prev]
      const target = index + dir
      if (target < 0 || target >= next.length) return prev
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  }

  const deleteStep = (index) => {
    setSteps(prev => prev.filter((_, i) => i !== index))
  }

  const stepsValid = steps.length > 0 &&
    steps.every((s, i) => validateStep(s, i, steps) === null)

  const canRun = files.length > 0 && stepsValid && !running

  const handleRun = async () => {
    setRunError(null); setRunning(true); setJobId(null); setJobStatus(null)
    try {
      const fd = new FormData()
      files.forEach(f => fd.append('files', f))
      fd.append('steps', JSON.stringify(steps.map(s => ({ type: s.type, ...s.config }))))
      const res = await fetch(`${API}/pipeline/run`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      const { job_id } = await res.json()
      setJobId(job_id)
    } catch (e) {
      setRunError(e.message)
      setRunning(false)
    }
  }

  const handleReset = () => {
    if (jobId) fetch(`${API}/pipeline/${jobId}`, { method: 'DELETE' }).catch(() => {})
    setJobId(null); setJobStatus(null); setRunning(false); setRunError(null)
  }

  const showProgress = running || jobStatus

  return (
    <div className="tab-content">
      <div className="batch-layout">

        {/* ── Left: files ── */}
        <div className="batch-left">
          {/* drag + drop / click to pick individual files */}
          <div
            className={`dropzone ${dragging ? 'dragging' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => {
              e.preventDefault(); setDragging(false)
              if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files)
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--muted)' }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p className="dropzone-label">
              {files.length > 0 ? `${files.length} images loaded` : 'drop sprites here'}
            </p>
            <p className="dropzone-hint">PNG, JPG, BMP · click or drag</p>
          </div>

          {/* hidden file inputs */}
          <input ref={fileInputRef} type="file" multiple accept="image/*" style={{ display: 'none' }}
            onChange={e => { if (e.target.files.length) handleFiles(e.target.files); e.target.value = '' }} />
          <input ref={folderInputRef} type="file" multiple
            // @ts-ignore
            webkitdirectory="true"
            accept="image/*" style={{ display: 'none' }}
            onChange={e => { if (e.target.files.length) handleFiles(e.target.files); e.target.value = '' }} />

          {/* folder fallback button */}
          <button className="batch-folder-btn" onClick={() => folderInputRef.current?.click()}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            select folder instead
          </button>

          {files.length > 0 && (
            <div className="batch-file-list">
              {files.slice(0, 12).map(f => (
                <div key={f.name} className="batch-file-row">
                  <span className="batch-file-name">{f.name}</span>
                  <span className="batch-file-size">{(f.size / 1024).toFixed(0)}kb</span>
                </div>
              ))}
              {files.length > 12 && (
                <div className="batch-file-more">+{files.length - 12} more</div>
              )}
            </div>
          )}

          {files.length === 0 && (
            <div className="batch-left-hint">
              <p>Drop individual sprites, multi-select files, or pick a whole folder.</p>
              <p>Supported: PNG, JPG, BMP, GIF</p>
            </div>
          )}
        </div>

        {/* ── Right: pipeline ── */}
        <div className="batch-right">
          <div className="batch-toolbar">
            <span className="section-label">
              pipeline
              {steps.length > 0 && <span className="batch-step-count">{steps.length} steps</span>}
            </span>
            <button className="btn-run" disabled={!canRun} onClick={handleRun}>
              {running
                ? <><Loader size={12} className="spinning"/> running…</>
                : <><Play size={12}/> run {files.length > 0 ? `(${files.length})` : ''}</>
              }
            </button>
          </div>

          {runError && <p className="error-msg">{runError}</p>}

          {steps.length === 0 && !showProgress && (
            <div className="batch-empty">
              <p>Add steps below to build your pipeline.</p>
              <p>Steps run in order on every image.</p>
            </div>
          )}

          <div className="step-list">
            {steps.map((step, i) => (
              <StepCard key={step.id} step={step} index={i} total={steps.length} allSteps={steps}
                onChange={updateStepConfig} onMove={moveStep} onDelete={deleteStep}
                palettes={palettes} presets={presets} />
            ))}
          </div>

          {!showProgress && (
            <div className="add-step-row">
              <span className="add-step-label">add step</span>
              <button className="add-step-btn add-step-btn--extract" onClick={() => addStep('extract')}>+ extract palette</button>
              <button className="add-step-btn add-step-btn--tileset" onClick={() => addStep('tileset')}>+ apply preset</button>
              <button className="add-step-btn add-step-btn--convert" onClick={() => addStep('convert')}>+ apply palette</button>
            </div>
          )}

          {showProgress && jobStatus && (
            <ProgressPanel status={jobStatus} jobId={jobId} onReset={handleReset} />
          )}
        </div>
      </div>
    </div>
  )
}