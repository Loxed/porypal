import { useState, useEffect, useRef } from 'react'
import './PalettesTab.css'
import { PaletteStrip } from '../components/PaletteStrip'
import { RefreshCw, Upload, Trash2, Download, BookOpen, ChevronDown, ChevronRight, Check, X } from 'lucide-react'

const API = '/api'

const SOURCE_LABELS = { default: 'defaults', user: 'my palettes', legacy: 'other' }
const SOURCE_ORDER  = ['default', 'user', 'legacy']

// ---------------------------------------------------------------------------
// Loaded palette row
// ---------------------------------------------------------------------------
function PaletteRow({ palette, onDelete, onDownload }) {
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleDelete = () => {
    if (!confirmDelete) { setConfirmDelete(true); return }
    onDelete(palette.name)
  }

  return (
    <div className={`pal-row ${confirmDelete ? 'pal-row--confirm' : ''}`}>
      <div className="pal-row-info">
        <span className="pal-row-name">{palette.name.replace('.pal', '')}</span>
        <span className="pal-row-count">{palette.count} colors</span>
      </div>
      <div className="pal-row-strip">
        <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
      </div>
      <div className="pal-row-actions">
        <button className="pal-icon-btn" title="download .pal" onClick={() => onDownload(palette.name)}>
          <Download size={12} />
        </button>
        {!palette.is_default && (
          <button
            className={`pal-icon-btn pal-icon-btn--danger ${confirmDelete ? 'confirming' : ''}`}
            title={confirmDelete ? 'click again to confirm' : 'delete palette'}
            onClick={handleDelete}
            onBlur={() => setConfirmDelete(false)}
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Library palette row
// ---------------------------------------------------------------------------
function LibraryRow({ palette, onImport, imported }) {
  const [state, setState] = useState('idle') // idle | importing | done | error

  const handleImport = async () => {
    if (state !== 'idle') return
    setState('importing')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: palette.path }),
      })
      if (!res.ok) throw new Error()
      setState('done')
      onImport()
      setTimeout(() => setState('idle'), 2000)
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 2000)
    }
  }

  return (
    <div className="lib-row">
      <span className="lib-row-name">{palette.name.replace('.pal', '')}</span>
      <div className="lib-row-strip">
        <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
      </div>
      <button
        className={`lib-import-btn ${state}`}
        onClick={handleImport}
        disabled={state === 'importing'}
        title="import to my palettes"
      >
        {state === 'done'
          ? <><Check size={11} /> added</>
          : state === 'error'
          ? <>failed</>
          : <>+ add</>
        }
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Collapsible category block
// ---------------------------------------------------------------------------
function CategoryBlock({ category, palettes, onImport }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="lib-category">
      <button className="lib-category-header" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span className="lib-category-name">{category}</span>
        <span className="lib-category-count">{palettes.length}</span>
      </button>
      {open && (
        <div className="lib-category-list">
          {palettes.map(p => (
            <LibraryRow key={p.path} palette={p} onImport={onImport} />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Game block
// ---------------------------------------------------------------------------
function GameBlock({ game, categories, query, onImport }) {
  const [open, setOpen] = useState(true)

  // Filter by search query
  const filtered = categories.map(c => ({
    ...c,
    palettes: c.palettes.filter(p =>
      !query || p.name.toLowerCase().includes(query.toLowerCase())
    ),
  })).filter(c => c.palettes.length > 0)

  if (filtered.length === 0) return null

  const total = filtered.reduce((n, c) => n + c.palettes.length, 0)

  return (
    <div className="lib-game">
      <button className="lib-game-header" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-game-name">{game}</span>
        <span className="lib-game-count">{total}</span>
      </button>
      {open && (
        <div className="lib-game-body">
          {filtered.map(c => (
            <CategoryBlock
              key={c.category}
              category={c.category}
              palettes={c.palettes}
              onImport={onImport}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Library drawer
// ---------------------------------------------------------------------------
function LibraryDrawer({ onClose, onImport }) {
  const [tree, setTree]     = useState(null)
  const [query, setQuery]   = useState('')
  const [loading, setLoading] = useState(true)
  const drawerRef = useRef()

  useEffect(() => {
    fetch(`${API}/palette-library`)
      .then(r => r.json())
      .then(data => { setTree(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  const totalPalettes = tree?.reduce((n, g) =>
    n + g.categories.reduce((m, c) => m + c.palettes.length, 0), 0) ?? 0

  return (
    <div className="drawer-overlay">
      <div className="drawer" ref={drawerRef}>

        <div className="drawer-header">
          <div className="drawer-title-row">
            <span className="drawer-title">palette library</span>
            {!loading && <span className="drawer-total">{totalPalettes} palettes</span>}
            <button className="drawer-close" onClick={onClose}><X size={15} /></button>
          </div>
          <input
            className="drawer-search"
            placeholder="search…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
        </div>

        <div className="drawer-body">
          {loading && <div className="empty-state"><div className="spinner" /></div>}

          {!loading && tree?.length === 0 && (
            <div className="drawer-empty">
              <p>No palettes in library yet.</p>
              <p>Add <code>.pal</code> files to <code>palette_library/&lt;game&gt;/&lt;category&gt;/</code></p>
            </div>
          )}

          {!loading && tree?.map(g => (
            <GameBlock
              key={g.game}
              game={g.game}
              categories={g.categories}
              query={query}
              onImport={onImport}
            />
          ))}
        </div>

      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main tab
// ---------------------------------------------------------------------------
export function PalettesTab() {
  const [palettes, setPalettes]     = useState([])
  const [loading, setLoading]       = useState(false)
  const [reloading, setReloading]   = useState(false)
  const [error, setError]           = useState(null)
  const [showLibrary, setShowLibrary] = useState(false)
  const fileRef = useRef()

  const fetchPalettes = async () => {
    setLoading(true)
    try {
      const data = await fetch(`${API}/palettes`).then(r => r.json())
      setPalettes(data)
    } catch {
      setError('Failed to load palettes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPalettes() }, [])

  const handleReload = async () => {
    setReloading(true)
    await fetch(`${API}/palettes/reload`, { method: 'POST' })
    await fetchPalettes()
    setReloading(false)
  }

  const handleUpload = async (files) => {
    setError(null)
    await Promise.all(Array.from(files).map(async f => {
      const fd = new FormData()
      fd.append('file', f)
      const res = await fetch(`${API}/palettes/upload`, { method: 'POST', body: fd })
      if (!res.ok) setError(`Failed to upload ${f.name}`)
    }))
    await fetchPalettes()
  }

  const handleDelete = async (name) => {
    const res = await fetch(`${API}/palettes/${encodeURIComponent(name)}`, { method: 'DELETE' })
    if (!res.ok) { setError(await res.text()); return }
    await fetchPalettes()
  }

  const handleDownload = (name) => {
    const a = document.createElement('a')
    a.href = `${API}/palettes/${encodeURIComponent(name)}/download`
    a.download = name
    a.click()
  }

  const grouped = SOURCE_ORDER.reduce((acc, src) => {
    acc[src] = palettes.filter(p => p.source === src)
    return acc
  }, {})

  return (
    <div className="tab-content">
      {showLibrary && (
        <LibraryDrawer
          onClose={() => setShowLibrary(false)}
          onImport={fetchPalettes}
        />
      )}

      <div className="palettes-layout">

        {/* ── Left panel ── */}
        <div className="palettes-left">
          <div className="palettes-stats">
            <span className="palettes-stat-num">{palettes.length}</span>
            <span className="palettes-stat-label">palettes loaded</span>
          </div>

          <div className="palettes-stat-row">
            <div className="palettes-stat-item">
              <span className="palettes-stat-num">{grouped.default?.length ?? 0}</span>
              <span className="palettes-stat-label">defaults</span>
            </div>
            <div className="palettes-stat-item">
              <span className="palettes-stat-num">{grouped.user?.length ?? 0}</span>
              <span className="palettes-stat-label">user</span>
            </div>
          </div>

          <div className="palettes-left-actions">
            <button className="btn-secondary palettes-lib-btn" onClick={() => setShowLibrary(true)}>
              <BookOpen size={12} /> browse library
            </button>

            <button className="btn-secondary" onClick={() => fileRef.current?.click()}>
              <Upload size={12} /> upload .pal
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".pal"
              multiple
              style={{ display: 'none' }}
              onChange={e => { handleUpload(e.target.files); e.target.value = '' }}
            />

            <button className="btn-secondary" onClick={handleReload} disabled={reloading}>
              <RefreshCw size={12} className={reloading ? 'spinning' : ''} /> reload
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}

          <div className="palettes-left-hint">
            <p>Loaded palettes are used in the Convert and Batch tabs.</p>
            <p>Put <code>.pal</code> files in <code>palettes/user/</code> or upload above.</p>
            <p>Files in <code>palettes/defaults/</code> are read-only.</p>
          </div>
        </div>

        {/* ── Right panel: grouped list ── */}
        <div className="palettes-right">

          <div className="palettes-toolbar">
            <span className="section-label">loaded palettes</span>
          </div>

          {loading && <div className="empty-state"><div className="spinner" /></div>}

          {!loading && palettes.length === 0 && (
            <div className="empty-state">
              <p>no palettes loaded — browse the library or upload <code>.pal</code> files</p>
            </div>
          )}

          {!loading && SOURCE_ORDER.map(src => {
            const group = grouped[src]
            if (!group?.length) return null
            return (
              <div key={src} className="palettes-group">
                <div className="palettes-group-header">
                  <span className="section-label">{SOURCE_LABELS[src]}</span>
                  <span className="palettes-group-count">{group.length}</span>
                </div>
                <div className="palettes-group-list">
                  {group.map(p => (
                    <PaletteRow key={p.name} palette={p} onDelete={handleDelete} onDownload={handleDownload} />
                  ))}
                </div>
              </div>
            )
          })}

        </div>

      </div>
    </div>
  )
}