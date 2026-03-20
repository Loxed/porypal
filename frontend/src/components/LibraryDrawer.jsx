/**
 * frontend/src/components/LibraryDrawer.jsx
 */

import { useState, useEffect, useRef } from 'react'
import { X, ChevronDown, ChevronRight, Check, Loader, Download, FolderInput, Maximize2, Minimize2, FolderOpen, Trash2 } from 'lucide-react'
import { PaletteStrip } from './PaletteStrip'
import { PokemonCard } from './PokemonCard.jsx'
import { LibraryItemCard } from './LibraryItemCard.jsx'
import { ProjectLoader } from './ProjectLoader.jsx'
import { GenericFolderCard } from './GenericFolderCard.jsx'
import { TrainerCard } from './TrainerCard.jsx'
import './LibraryDrawer.css'

const API = '/api'
const PAGE_SIZE = 20

function wildcardMatch(pattern, str) {
  const p = pattern.toLowerCase()
  const s = str.toLowerCase()
  if (!p.includes('*') && !p.includes('?')) return s.includes(p)
  const regex = p
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*')
    .replace(/\?/g, '.')
  return new RegExp('^' + regex + '$').test(s)
}

// -- Standalone palette row -------------------------------------------------

function LibraryPaletteRow({ palette, onImport }) {
  const [state, setState] = useState('idle')

  const handleImport = async () => {
    if (state !== 'idle') return
    setState('loading')
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
      <span className="lib-row-name">{palette.name.replace(/\.pal$/, '')}</span>
      <div className="lib-row-strip">
        <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
      </div>
      <button className={`lib-import-btn ${state}`} onClick={handleImport} disabled={state === 'loading'}>
        {state === 'done' ? <><Check size={11} /> added</> : state === 'error' ? 'failed' : '+ add'}
      </button>
    </div>
  )
}

// -- Generic sprite row -----------------------------------------------------

function LibrarySpriteRow({ sprite }) {
  const [err, setErr] = useState(false)
  return (
    <div className="lib-row">
      <div className="lib-sprite-thumb">
        {!err
          ? <img className="lib-sprite-img"
              src={`${API}/palette-library/sprite?path=${encodeURIComponent(sprite.path)}`}
              alt={sprite.name} draggable={false} onError={() => setErr(true)} />
          : <div className="lib-sprite-img-missing" />
        }
      </div>
      <span className="lib-row-name">{sprite.name.replace(/\.png$/i, '')}</span>
    </div>
  )
}

// -- Paginated section base -------------------------------------------------

function usePaginatedSection(nodePath, query, fetchUrl) {
  const [open, setOpen]       = useState(false)
  const [items, setItems]     = useState([])
  const [total, setTotal]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset]   = useState(0)
  const sentinelRef           = useRef()

  useEffect(() => { setItems([]); setTotal(null); setOffset(0); setHasMore(false) }, [nodePath, query])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    const params = new URLSearchParams({ folder: nodePath, offset, limit: PAGE_SIZE })
    if (query) params.set('q', query)
    fetch(`${fetchUrl}?${params}`)
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
  }, [open, nodePath, query, offset, fetchUrl])

  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading) return
    const obs = new IntersectionObserver(
      entries => { if (entries[0].isIntersecting) setOffset(p => p + PAGE_SIZE) },
      { threshold: 0.1 }
    )
    obs.observe(sentinelRef.current)
    return () => obs.disconnect()
  }, [hasMore, loading])

  const toggle = () => {
    if (!open) { setItems([]); setTotal(null); setOffset(0); setHasMore(false) }
    setOpen(o => !o)
  }

  return { open, toggle, items, total, loading, hasMore, sentinelRef }
}

// -- Pokemon folder ---------------------------------------------------------

function PokemonFolderSection({ node, query, onImport, fullscreen }) {
  const { open, toggle, items, total, loading, hasMore, sentinelRef } =
    usePaginatedSection(node.path, query, `${API}/palette-library/pokemon`)

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={toggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {total !== null && <span className="lib-tree-folder-count">{total}</span>}
      </button>
      {open && (
        <div className="lib-tree-folder-body lib-pokemon-grid">
          {items.map((pkm, i) => (
            <PokemonCard key={pkm.path ?? i} node={pkm} onImport={onImport} fullscreen={fullscreen} />
          ))}
          {loading && <div className="lib-pokemon-loading"><Loader size={13} className="spinning" /> loading...</div>}
          {!loading && hasMore && <div ref={sentinelRef} className="lib-pokemon-sentinel" />}
          {!loading && !hasMore && total !== null && items.length === 0 && (
            <div className="lib-pokemon-empty">no entries found</div>
          )}
        </div>
      )}
    </div>
  )
}

// -- Items folder -----------------------------------------------------------

function ItemsFolderSection({ node, query, onImport }) {
  const { open, toggle, items, total, loading, hasMore, sentinelRef } =
    usePaginatedSection(node.path, query, `${API}/palette-library/items`)

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={toggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {total !== null && <span className="lib-tree-folder-count">{total}</span>}
      </button>
      {open && (
        <div className="lib-tree-folder-body lib-pokemon-grid">
          {items.map((item, i) => (
            <LibraryItemCard key={item.name ?? i} item={item} onImport={onImport} />
          ))}
          {loading && <div className="lib-pokemon-loading"><Loader size={13} className="spinning" /> loading...</div>}
          {!loading && hasMore && <div ref={sentinelRef} className="lib-pokemon-sentinel" />}
          {!loading && !hasMore && total !== null && items.length === 0 && (
            <div className="lib-pokemon-empty">no items found</div>
          )}
        </div>
      )}
    </div>
  )
}

// -- Generic folder ---------------------------------------------------------

function GenericFolderSection({ node, query, onImport, depth }) {
  const [open, setOpen]         = useState(false)
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

  // fetch only when user explicitly opens

  const toggle = () => {
    if (!open && children === null) fetchChildren()
    setOpen(o => !o)
  }

  // Never hide a folder based on query — let the children filter themselves.
  // An open folder with no matching children will just show empty.

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={toggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {loading && <Loader size={11} className="spinning" />}
      </button>
      {open && (
        <div className="lib-tree-folder-body">
          {loading && <div className="lib-pokemon-loading"><Loader size={12} className="spinning" /> loading...</div>}
          {children && (() => {
            const subFolders = children.filter(n => n.type === 'folder' || n.type === 'pokemon_folder' || n.type === 'items_folder' || n.type === 'trainers_folder')
            const files      = children.filter(n => n.type === 'sprite' || n.type === 'palette')
            return <>
              {subFolders.map((child, i) => (
                <LibraryNode key={i} node={child} query={query} onImport={onImport} depth={depth + 1} />
              ))}
              {files.length > 0 && <GenericFolderCard nodes={files} onImport={onImport} query={query} />}
            </>
          })()}
          {children?.length === 0 && !loading && <div className="lib-pokemon-empty">empty</div>}
        </div>
      )}
    </div>
  )
}

// -- Trainers folder --------------------------------------------------------

function TrainerFolderSection({ node, query, onImport }) {
  const [open, setOpen]         = useState(false)
  const [nodes, setNodes]       = useState(null)
  const [loading, setLoading]   = useState(false)

  const fetchNodes = async () => {
    if (nodes !== null || loading) return
    setLoading(true)
    try {
      // Fetch trainers/ top level → front_pics/, back_pics/, palettes/ sub-folders
      const res = await fetch(`${API}/palette-library/folder?path=${encodeURIComponent(node.path)}`)
      if (!res.ok) throw new Error()
      const topLevel = await res.json()

      // Fetch each sub-folder and tag nodes with their sub-folder name so
      // TrainerCard knows if it's front_pics vs back_pics vs palettes
      const subFolders = topLevel.filter(n => n.type === 'folder')
      const subFetches = subFolders.map(n =>
        fetch(`${API}/palette-library/folder?path=${encodeURIComponent(n.path)}`)
          .then(r => r.json())
          .then(children => children.map(c => ({ ...c, _subfolder: n.name })))
          .catch(() => [])
      )
      const subResults = await Promise.all(subFetches)
      const flat = subResults.flat()
      const rootFiles = topLevel.filter(n => n.type !== 'folder')
      setNodes([...rootFiles, ...flat])
    } catch (e) {
      console.error('TrainerFolderSection fetch error:', e)
      setNodes([])
    } finally {
      setLoading(false)
    }
  }

  const toggle = () => {
    if (!open && nodes === null) fetchNodes()
    setOpen(o => !o)
  }

  return (
    <div className="lib-tree-folder">
      <button className="lib-tree-folder-header" onClick={toggle}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="lib-tree-folder-name">{node.name}</span>
        {loading && <Loader size={11} className="spinning" />}
      </button>
      {open && (
        <div className="lib-tree-folder-body">
          {loading && <div className="lib-pokemon-loading"><Loader size={12} className="spinning" /> loading...</div>}
          {nodes && <TrainerCard nodes={nodes} onImport={onImport} query={query} />}
          {nodes?.length === 0 && !loading && <div className="lib-pokemon-empty">empty</div>}
        </div>
      )}
    </div>
  )
}

// -- Tree node router -------------------------------------------------------

function LibraryNode({ node, query, onImport, depth = 0, fullscreen }) {
  if (node.type === 'pokemon_folder')
    return <PokemonFolderSection node={node} query={query} onImport={onImport} fullscreen={fullscreen} />
  if (node.type === 'trainers_folder')
    return <TrainerFolderSection node={node} query={query} onImport={onImport} />
  if (node.type === 'items_folder')
    return <ItemsFolderSection node={node} query={query} onImport={onImport} />
  if (node.type === 'palette') {
    if (query && !wildcardMatch(query, node.name.replace(/\.pal$/, ''))) return null
    return <LibraryPaletteRow palette={node} onImport={onImport} />
  }
  if (node.type === 'sprite') {
    if (query && !wildcardMatch(query, node.name.replace(/\.png$/i, ''))) return null
    return <LibrarySpriteRow sprite={node} />
  }
  return <GenericFolderSection node={node} query={query} onImport={onImport} depth={depth} fullscreen={fullscreen} />
}

// -- Section header — used to label palette_library vs each project ---------

function SectionHeader({ label, path, onRemove }) {
  return (
    <div className="lib-section-header">
      <span className="lib-section-label">{label}</span>
      <span className="lib-section-path">{path}</span>
      {onRemove && (
        <button className="lib-section-remove" onClick={onRemove} title="Remove project">
          <Trash2 size={11} />
        </button>
      )}
    </div>
  )
}

// -- Drawer -----------------------------------------------------------------

export function LibraryDrawer({ onClose, onImport }) {
  const [tree, setTree]                = useState(null)
  const [projects, setProjects]        = useState([])
  const [query, setQuery]              = useState('')
  const [debouncedQuery, setDebounced] = useState('')
  const [loading, setLoading]          = useState(true)
  const [fullscreen, setFullscreen]    = useState(false)
  const [showLoader, setShowLoader]    = useState(false)
  const drawerRef   = useRef()
  const debounceRef = useRef()
  const showLoaderRef = useRef(false)

  const fetchTree = () => {
    setLoading(true)
    Promise.all([
      fetch(`${API}/palette-library`).then(r => r.json()),
      fetch(`${API}/palette-library/projects`).then(r => r.json()),
    ])
      .then(([treeData, projectsData]) => {
        setTree(treeData)
        setProjects(projectsData)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchTree() }, [])
  useEffect(() => { showLoaderRef.current = showLoader }, [showLoader])

  useEffect(() => {
    if (fullscreen) return
    const handler = e => {
      if (showLoaderRef.current) return
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

  const handleRemoveProject = async (name) => {
    await fetch(`${API}/palette-library/projects/${encodeURIComponent(name)}`, { method: 'DELETE' })
    fetchTree()
  }

  // Split tree nodes: local palette_library nodes vs project nodes
  const localNodes   = tree?.filter(n => !n.project) ?? []
  const projectNodes = tree?.filter(n =>  n.project) ?? []

  // Group project nodes by project name
  const projectGroups = new Map()
  for (const node of projectNodes) {
    if (!projectGroups.has(node.project)) projectGroups.set(node.project, [])
    projectGroups.get(node.project).push(node)
  }

  return (
    <>
      {showLoader && (
        <ProjectLoader
          onClose={() => setShowLoader(false)}
          onLoaded={() => { setShowLoader(false); fetchTree() }}
        />
      )}
      <div className={`drawer-overlay ${fullscreen ? 'drawer-overlay--fullscreen' : ''}`}>
        <div className={`drawer ${fullscreen ? 'drawer--fullscreen' : ''}`} ref={drawerRef}>

          <div className="drawer-header">
            <div className="drawer-title-row">
              <button className="drawer-fullscreen-btn" onClick={() => setFullscreen(f => !f)}
                title={fullscreen ? 'Restore' : 'Expand'}>
                {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
              <span className="drawer-title">palette library</span>
              <button className="drawer-load-project-btn" onClick={() => setShowLoader(true)}>
                <FolderOpen size={13} /> Load Project…
              </button>
              <button className="drawer-close" onClick={onClose}><X size={15} /></button>
            </div>
            <input className="drawer-search" placeholder="search library…"
              value={query} onChange={handleSearch} autoFocus />
          </div>

          <div className={`drawer-body ${fullscreen ? 'drawer-body--fullscreen' : ''}`}>
            {loading && <div className="empty-state"><div className="spinner" /></div>}

            {!loading && localNodes.length === 0 && projectGroups.size === 0 && (
              <div className="drawer-empty">
                <p>No palettes in library yet.</p>
                <p>Add <code>.pal</code> files to <code>palette_library/</code></p>
                <p>or use <strong>Load Project…</strong> to browse a ROM hack folder.</p>
              </div>
            )}

            {/* ── palette_library/ section ─────────────────────────────── */}
            {!loading && (localNodes.length > 0 || projectGroups.size === 0) && (
              <div className="lib-source-section">
                <SectionHeader label="palette_library" path="porypal/palette_library/" />
                {localNodes.length === 0
                  ? <p className="lib-source-empty">empty — drop .pal files here</p>
                  : localNodes.map((node, i) => (
                      <LibraryNode key={i} node={node} query={debouncedQuery}
                        onImport={onImport} depth={0} fullscreen={fullscreen} />
                    ))
                }
              </div>
            )}

            {/* ── Loaded projects ──────────────────────────────────────── */}
            {!loading && [...projectGroups.entries()].map(([projName, nodes]) => {
              // Find the root path for this project
              const proj = projects.find(p => p.name === projName)
              const rootPath = proj?.root ?? projName
              return (
                <div key={projName} className="lib-source-section lib-source-section--project">
                  <SectionHeader
                    label={projName}
                    path={rootPath}
                    onRemove={() => handleRemoveProject(projName)}
                  />
                  {nodes.map((node, i) => (
                    <LibraryNode key={i} node={node} query={debouncedQuery}
                      onImport={onImport} depth={0} fullscreen={fullscreen} />
                  ))}
                </div>
              )
            })}
          </div>

        </div>
      </div>
    </>
  )
}