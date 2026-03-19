/**
 * frontend/src/components/LibraryDrawer.jsx
 */

import { useState, useEffect, useRef } from 'react'
import { X, ChevronDown, ChevronRight, Check, Loader, Download, FolderInput, Maximize2, Minimize2 } from 'lucide-react'
import { PaletteStrip } from './PaletteStrip'
import { PokemonCard } from './PokemonCard.jsx'
import './LibraryDrawer.css'

const API = '/api'
const PAGE_SIZE = 20

// ── Standalone palette row ─────────────────────────────────────────────────

function LibraryPaletteRow({ palette, onImport }) {
  const [importState, setImportState] = useState('idle')

  const handleImport = async () => {
    if (importState !== 'idle') return
    setImportState('importing')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: palette.path }),
      })
      if (!res.ok) throw new Error()
      setImportState('done')
      onImport()
      setTimeout(() => setImportState('idle'), 2000)
    } catch {
      setImportState('error')
      setTimeout(() => setImportState('idle'), 2000)
    }
  }

  return (
    <div className="lib-row">
      <span className="lib-row-name">{palette.name.replace(/\.pal$/, '')}</span>
      <div className="lib-row-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
      <button
        className={`lib-import-btn ${importState}`}
        onClick={handleImport}
        disabled={importState === 'importing'}
      >
        {importState === 'done'
          ? <><Check size={11} /> added</>
          : importState === 'error'
          ? 'failed'
          : '+ add'}
      </button>
    </div>
  )
}

// ── Pokemon / Trainers folder ──────────────────────────────────────────────

function PokemonFolderSection({ node, query, onImport, fullscreen }) {
  const [open, setOpen]       = useState(false)
  const [items, setItems]     = useState([])
  const [total, setTotal]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset]   = useState(0)
  const sentinelRef           = useRef()

  useEffect(() => {
    setItems([])
    setTotal(null)
    setOffset(0)
    setHasMore(false)
  }, [node.path, query])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    const params = new URLSearchParams({ folder: node.path, offset, limit: PAGE_SIZE })
    if (query) params.set('q', query)
    fetch(`${API}/palette-library/pokemon?${params}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setItems(prev => offset === 0 ? data.items : [...prev, ...data.items])
        setTotal(data.total)
        setHasMore(data.has_more)
        setLoading(false)
      })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [open, node.path, query, offset])

  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading) return
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) setOffset(prev => prev + PAGE_SIZE)
    }, { threshold: 0.1 })
    obs.observe(sentinelRef.current)
    return () => obs.disconnect()
  }, [hasMore, loading])

  const handleToggle = () => {
    if (!open) { setItems([]); setTotal(null); setOffset(0); setHasMore(false) }
    setOpen(o => !o)
  }

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={handleToggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {total !== null && <span className="lib-tree-folder-count">{total}</span>}
      </button>
      {open && (
        <div className="lib-tree-folder-body lib-pokemon-grid">
          {items.map((pkm, i) => (
            <PokemonCard key={pkm.path ?? i} node={pkm} onImport={onImport} fullscreen={fullscreen} />
          ))}
          {loading && (
            <div className="lib-pokemon-loading">
              <Loader size={13} className="spinning" /> loading…
            </div>
          )}
          {!loading && hasMore && <div ref={sentinelRef} className="lib-pokemon-sentinel" />}
          {!loading && !hasMore && total !== null && items.length === 0 && (
            <div className="lib-pokemon-empty">no entries found</div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Items folder ───────────────────────────────────────────────────────────

function ItemRow({ item, onImport }) {
  const [importState, setImportState] = useState('idle')

  const handleImport = async () => {
    if (!item.palette_path || importState !== 'idle') return
    setImportState('importing')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: item.palette_path }),
      })
      if (!res.ok) throw new Error()
      setImportState('done')
      onImport()
      setTimeout(() => setImportState('idle'), 2000)
    } catch {
      setImportState('error')
      setTimeout(() => setImportState('idle'), 2000)
    }
  }

  return (
    <div className="lib-item-row">
      <div className="lib-item-thumb">
        {item.sprite_path ? (
          <img
            className="lib-item-img"
            src={`${API}/palette-library/sprite?path=${encodeURIComponent(item.sprite_path)}`}
            alt={item.name}
            draggable={false}
            onError={e => { e.target.style.display = 'none' }}
          />
        ) : (
          <div className="lib-item-img-placeholder" />
        )}
      </div>

      <span className="lib-item-name" title={item.name}>{item.name}</span>

      <div className="lib-item-strip">
        {item.colors ? (
          <PaletteStrip
            colors={item.colors}
            usedIndices={item.colors.map((_, i) => i)}
            checkSize="50%"
          />
        ) : (
          <span className="lib-item-no-pal">no palette</span>
        )}
      </div>

      {item.palette_path && (
        <a
          className="lib-item-btn"
          href={`${API}/palette-library/sprite?path=${encodeURIComponent(item.palette_path)}`}
          download={item.name + '.pal'}
          title="Download .pal"
        >
          <Download size={11} />
        </a>
      )}

      <button
        className={`lib-item-btn ${!item.palette_path ? 'disabled' : ''} ${importState === 'done' ? 'done' : importState === 'error' ? 'err' : ''}`}
        onClick={handleImport}
        disabled={!item.palette_path || importState === 'importing'}
        title={item.palette_path ? 'Import to Porypal' : 'No palette available'}
      >
        {importState === 'done'
          ? <Check size={11} />
          : importState === 'error'
          ? <X size={11} />
          : importState === 'importing'
          ? <Loader size={11} className="spinning" />
          : <FolderInput size={11} />}
      </button>
    </div>
  )
}

function ItemsFolderSection({ node, query, onImport }) {
  const [open, setOpen]       = useState(false)
  const [items, setItems]     = useState([])
  const [total, setTotal]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset]   = useState(0)
  const sentinelRef           = useRef()

  useEffect(() => {
    setItems([])
    setTotal(null)
    setOffset(0)
    setHasMore(false)
  }, [node.path, query])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    const params = new URLSearchParams({ folder: node.path, offset, limit: PAGE_SIZE })
    if (query) params.set('q', query)
    fetch(`${API}/palette-library/items?${params}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setItems(prev => offset === 0 ? data.items : [...prev, ...data.items])
        setTotal(data.total)
        setHasMore(data.has_more)
        setLoading(false)
      })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [open, node.path, query, offset])

  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading) return
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) setOffset(prev => prev + PAGE_SIZE)
    }, { threshold: 0.1 })
    obs.observe(sentinelRef.current)
    return () => obs.disconnect()
  }, [hasMore, loading])

  const handleToggle = () => {
    if (!open) { setItems([]); setTotal(null); setOffset(0); setHasMore(false) }
    setOpen(o => !o)
  }

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={handleToggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {total !== null && <span className="lib-tree-folder-count">{total}</span>}
      </button>
      {open && (
        <div className="lib-tree-folder-body">
          {items.map((item, i) => (
            <ItemRow key={item.name ?? i} item={item} onImport={onImport} />
          ))}
          {loading && (
            <div className="lib-pokemon-loading">
              <Loader size={13} className="spinning" /> loading…
            </div>
          )}
          {!loading && hasMore && <div ref={sentinelRef} className="lib-pokemon-sentinel" />}
          {!loading && !hasMore && total !== null && items.length === 0 && (
            <div className="lib-pokemon-empty">no items found</div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Generic lazy folder ────────────────────────────────────────────────────

function LazyFolderNode({ node, query, onImport, depth, fullscreen }) {
  const [open, setOpen]         = useState(depth < 1)
  const [children, setChildren] = useState(node.children ?? null)
  const [loading, setLoading]   = useState(false)

  const fetchChildren = async () => {
    if (children !== null || loading) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/palette-library/folder?path=${encodeURIComponent(node.path)}`)
      if (!res.ok) throw new Error()
      setChildren(await res.json())
    } catch {
      setChildren([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && children === null) fetchChildren()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleToggle = () => {
    if (!open && children === null) fetchChildren()
    setOpen(o => !o)
  }

  const hasMatch = query
    ? (() => {
        if (!children) return true
        const check = (n) => {
          if (n.type === 'palette') return n.name.replace(/\.pal$/, '').toLowerCase().includes(query.toLowerCase())
          if (n.type === 'pokemon_folder' || n.type === 'trainers_folder' || n.type === 'items_folder')
            return n.name.toLowerCase().includes(query.toLowerCase())
          return n.children?.some(check) ?? true
        }
        return children.some(check)
      })()
    : true

  if (!hasMatch) return null

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={handleToggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {loading && <Loader size={11} className="spinning" />}
      </button>
      {open && (
        <div className="lib-tree-folder-body">
          {loading && (
            <div className="lib-pokemon-loading">
              <Loader size={12} className="spinning" /> loading…
            </div>
          )}
          {children?.map((child, i) => (
            <LibraryNode key={i} node={child} query={query} onImport={onImport} depth={depth + 1} fullscreen={fullscreen} />
          ))}
          {children?.length === 0 && !loading && (
            <div className="lib-pokemon-empty">empty</div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Tree node router ───────────────────────────────────────────────────────

function LibraryNode({ node, query, onImport, depth = 0, fullscreen }) {
  if (node.type === 'pokemon_folder' || node.type === 'trainers_folder') {
    return <PokemonFolderSection node={node} query={query} onImport={onImport} fullscreen={fullscreen} />
  }
  if (node.type === 'items_folder') {
    return <ItemsFolderSection node={node} query={query} onImport={onImport} />
  }
  if (node.type === 'palette') {
    const name = node.name.replace(/\.pal$/, '')
    if (query && !name.toLowerCase().includes(query.toLowerCase())) return null
    return <LibraryPaletteRow palette={node} onImport={onImport} />
  }
  return <LazyFolderNode node={node} query={query} onImport={onImport} depth={depth} fullscreen={fullscreen} />
}

// ── Drawer ─────────────────────────────────────────────────────────────────

export function LibraryDrawer({ onClose, onImport }) {
  const [tree, setTree]                = useState(null)
  const [query, setQuery]              = useState('')
  const [debouncedQuery, setDebounced] = useState('')
  const [loading, setLoading]          = useState(true)
  const [fullscreen, setFullscreen]    = useState(false)
  const drawerRef   = useRef()
  const debounceRef = useRef()

  useEffect(() => {
    fetch(`${API}/palette-library`)
      .then(r => r.json())
      .then(data => { setTree(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  // Close on outside click (only when not fullscreen)
  useEffect(() => {
    if (fullscreen) return
    const handler = e => {
      if (drawerRef.current && !drawerRef.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose, fullscreen])

  const handleSearch = e => {
    const val = e.target.value
    setQuery(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setDebounced(val), 300)
  }

  return (
    <div className={`drawer-overlay ${fullscreen ? 'drawer-overlay--fullscreen' : ''}`}>
      <div
        className={`drawer ${fullscreen ? 'drawer--fullscreen' : ''}`}
        ref={drawerRef}
      >
        <div className="drawer-header">
          <div className="drawer-title-row">
            <button
              className="drawer-fullscreen-btn"
              onClick={() => setFullscreen(f => !f)}
              title={fullscreen ? 'Restore drawer' : 'Expand to full page'}
            >
              {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <span className="drawer-title">palette library</span>
            <button className="drawer-close" onClick={onClose}><X size={15} /></button>
          </div>
          <input
            className="drawer-search"
            placeholder="search library…"
            value={query}
            onChange={handleSearch}
            autoFocus
          />
        </div>
        <div className={`drawer-body ${fullscreen ? 'drawer-body--fullscreen' : ''}`}>
          {loading && (
            <div className="empty-state"><div className="spinner" /></div>
          )}
          {!loading && (!tree || tree.length === 0) && (
            <div className="drawer-empty">
              <p>No palettes in library yet.</p>
              <p>Add <code>.pal</code> files to <code>palette_library/</code></p>
            </div>
          )}
          {!loading && tree?.map((node, i) => (
            <LibraryNode
              key={i}
              node={node}
              query={debouncedQuery}
              onImport={onImport}
              depth={0}
              fullscreen={fullscreen}
            />
          ))}
        </div>
      </div>
    </div>
  )
}