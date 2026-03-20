import { useState, useEffect, useRef } from 'react'
import './PalettesTab.css'
import { PaletteStrip } from '../components/PaletteStrip'
import { Modal } from '../components/Modal'
import { LibraryDrawer } from '../components/Library'
import {
  RefreshCw, Upload, Trash2, Download, BookOpen,
  ChevronDown, ChevronRight, Check, X, FolderPlus,
  Move, Palette, GripVertical, Folder, FolderOpen, Plus, Minus,
} from 'lucide-react'

const API = '/api'

// ─────────────────────────────────────────────────────────────────────────────
// Color editor (inline expand on a palette row)
// ─────────────────────────────────────────────────────────────────────────────

function ColorEditor({ palette, onSave, onCancel }) {
  const [colors, setColors]         = useState([...palette.colors])
  const [activeSlot, setActiveSlot] = useState(null)
  const [hexInput, setHexInput]     = useState('')
  const [saveState, setSaveState]   = useState('idle') // idle | confirm | saving | saved | error
  const [dragSrc, setDragSrc]       = useState(null)
  const [dragOver, setDragOver]     = useState(null)
  const [cacheCount, setCacheCount] = useState(0)
  const removedStack = useRef([])
  const HEX_RE = /^#[0-9a-fA-F]{6}$/

  const selectSlot = (i) => {
    setActiveSlot(i)
    setHexInput(colors[i])
  }

  const commitHex = () => {
    if (activeSlot === null) return
    const val = hexInput.trim()
    if (HEX_RE.test(val)) {
      const next = [...colors]
      next[activeSlot] = val.toUpperCase()
      setColors(next)
    } else {
      setHexInput(colors[activeSlot])
    }
  }

  const handleSlotDragStart = (e, i) => {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(i))
    setDragSrc(i)
  }
  const handleSlotDragOver = (e, i) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(i)
  }
  const handleSlotDrop = (e, i) => {
    e.preventDefault()
    const src = dragSrc
    setDragSrc(null); setDragOver(null)
    if (src === null || src === i) return
    const next = [...colors]
    ;[next[src], next[i]] = [next[i], next[src]]
    if (activeSlot === src) setActiveSlot(i)
    else if (activeSlot === i) setActiveSlot(src)
    setColors(next)
  }
  const handleSlotDragEnd = () => { setDragSrc(null); setDragOver(null) }

  const removeColor = () => {
    if (colors.length <= 1) return
    const popped = colors[colors.length - 1]
    removedStack.current.push(popped)
    setCacheCount(removedStack.current.length)
    if (activeSlot !== null && activeSlot >= colors.length - 1) setActiveSlot(null)
    setColors(prev => prev.slice(0, -1))
  }

  const addColor = () => {
    if (colors.length >= 16) return
    const restored = removedStack.current.length > 0
      ? removedStack.current.pop()
      : '#000000'
    setCacheCount(removedStack.current.length)
    setColors(prev => [...prev, restored])
  }

  const handleSaveClick = () => {
    if (saveState === 'idle') { setSaveState('confirm'); return }
  }
  const handleConfirm = async () => {
    setSaveState('saving')
    removedStack.current = []
    setCacheCount(0)
    try {
      const res = await fetch(`${API}/palettes/${encodeURIComponent(palette.path)}/colors`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ colors }),
      })
      if (!res.ok) throw new Error()
      setSaveState('saved')
      setTimeout(() => { setSaveState('idle'); onSave(colors) }, 900)
    } catch {
      setSaveState('error')
      setTimeout(() => setSaveState('idle'), 2000)
    }
  }
  const handleCancelConfirm = () => setSaveState('idle')

  return (
    <div className="pal-color-editor">
      <div className="pal-editor-count-row">
        <span className="pal-editor-count-label">{colors.length} / 16 slots</span>
        <div className="pal-editor-count-btns">
          <button
            className="pal-editor-count-btn"
            onClick={removeColor}
            disabled={colors.length <= 1}
            title={`remove slot ${colors.length - 1} (saves to cache)`}
          >
            <Minus size={11} />
          </button>

          {cacheCount > 0 && (
            <div
              className="pal-editor-cache-swatch"
              style={{ background: removedStack.current[removedStack.current.length - 1] }}
              title={`next restore: ${removedStack.current[removedStack.current.length - 1]}`}
            />
          )}

          <button
            className="pal-editor-count-btn"
            onClick={addColor}
            disabled={colors.length >= 16}
            title={cacheCount > 0
              ? `restore ${removedStack.current[removedStack.current.length - 1]} (${cacheCount} in cache)`
              : 'add black slot'}
          >
            <Plus size={11} />
          </button>

          {cacheCount > 0 && (
            <span className="pal-editor-cache-hint" title="colors saved in stack">
              {cacheCount} cached
            </span>
          )}
        </div>
      </div>

      <div className="pal-editor-strip">
        {colors.map((hex, i) => (
          <div
            key={i}
            className={`pal-editor-slot
              ${activeSlot === i ? 'is-active' : ''}
              ${dragSrc === i ? 'is-dragging' : ''}
              ${dragOver === i && dragSrc !== i ? 'is-drop-target' : ''}
            `}
            draggable
            onDragStart={e => handleSlotDragStart(e, i)}
            onDragOver={e => handleSlotDragOver(e, i)}
            onDrop={e => handleSlotDrop(e, i)}
            onDragEnd={handleSlotDragEnd}
            onClick={() => selectSlot(i)}
            title={`slot ${i} — drag to swap`}
          >
            <div className="pal-editor-swatch" style={{ background: hex }} />
            <span className="pal-editor-idx">{i}</span>
          </div>
        ))}
      </div>

      {activeSlot !== null && activeSlot < colors.length && (
        <div className="pal-editor-hex-row">
          <div className="pal-editor-hex-swatch" style={{ background: colors[activeSlot] }} />
          <input
            className="pal-editor-hex-input"
            value={hexInput}
            onChange={e => setHexInput(e.target.value)}
            onBlur={commitHex}
            onKeyDown={e => {
              if (e.key === 'Enter') commitHex()
              if (e.key === 'Escape') setActiveSlot(null)
            }}
            maxLength={7}
            autoFocus
            spellCheck={false}
          />
          <span className="pal-editor-slot-label">
            slot {activeSlot}{activeSlot === 0 ? ' (transparent)' : ''}
          </span>
        </div>
      )}

      <div className="pal-editor-actions">
        {saveState === 'saved' && (
          <span className="pal-editor-saved-msg"><Check size={12} /> saved</span>
        )}
        {saveState === 'error' && (
          <button className="pal-editor-save-btn" onClick={() => setSaveState('idle')}>
            error — retry
          </button>
        )}
        {saveState === 'confirm' && (
          <>
            <span className="pal-editor-confirm-label">save {colors.length} colors to disk?</span>
            <button className="pal-editor-save-btn" onClick={handleConfirm}>
              <Check size={12} /> confirm
            </button>
            <button className="pal-editor-cancel-btn" onClick={handleCancelConfirm}>cancel</button>
          </>
        )}
        {(saveState === 'idle' || saveState === 'saving') && (
          <>
            <button
              className="pal-editor-save-btn"
              onClick={handleSaveClick}
              disabled={saveState === 'saving'}
            >
              {saveState === 'saving' ? 'saving…' : <><Palette size={12} /> save changes</>}
            </button>
            <button className="pal-editor-cancel-btn" onClick={onCancel}>cancel</button>
          </>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Move dropdown — uses fixed positioning to escape clipped containers
// ─────────────────────────────────────────────────────────────────────────────

function MoveDropdown({ folders, currentFolder, onMove }) {
  const [open, setOpen]       = useState(false)
  const [menuPos, setMenuPos] = useState({ top: 0, right: 0 })
  const btnRef = useRef()

  useEffect(() => {
    if (!open) return
    const handler = e => {
      if (!btnRef.current?.contains(e.target) && !document.getElementById('pal-move-menu')?.contains(e.target))
        setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const options = [
    { label: 'palettes/user  (root)', value: null },
    ...folders.map(f => ({ label: `palettes/user/${f}`, value: f })),
  ].filter(o => o.value !== currentFolder)

  if (options.length === 0) return null

  const handleOpen = e => {
    e.stopPropagation()
    if (!open) {
      const rect = btnRef.current.getBoundingClientRect()
      setMenuPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right })
    }
    setOpen(o => !o)
  }

  return (
    <>
      <button ref={btnRef} className="pal-icon-btn" title="move to folder" onClick={handleOpen}>
        <Move size={11} />
      </button>
      {open && (
        <div
          id="pal-move-menu"
          className="pal-move-menu"
          style={{ position: 'fixed', top: menuPos.top, right: menuPos.right, zIndex: 1000 }}
        >
          <p className="pal-move-menu-label">move to…</p>
          {options.map(o => (
            <button
              key={o.label}
              className="pal-move-menu-item"
              onClick={e => { e.stopPropagation(); setOpen(false); onMove(o.value) }}
            >
              <Folder size={11} /> {o.label}
            </button>
          ))}
        </div>
      )}
    </>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Palette row
// ─────────────────────────────────────────────────────────────────────────────

function PaletteRow({ palette, folders, onDelete, onDownload, onRename, onMove, onColorsUpdated }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [renaming, setRenaming]           = useState(false)
  const [renameVal, setRenameVal]         = useState(palette.name.replace(/\.pal$/, '').split('/').pop())
  const [editing, setEditing]             = useState(false)
  const [dragging, setDragging]           = useState(false)

  const palPath     = palette.path ?? palette.name
  const displayName = palPath.replace(/\.pal$/, '').split('/').pop()

  const commitRename = async () => {
    const stem = renameVal.trim()
    if (!stem || stem === displayName) { setRenaming(false); return }
    await onRename(palPath, stem)
    setRenaming(false)
  }

  const handleDelete = () => {
    if (!confirmDelete) { setConfirmDelete(true); return }
    onDelete(palPath)
  }

  const handleDragStart = e => {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ palettePath: palPath, folder: palette.folder ?? null }))
    setDragging(true)
  }

  return (
    <>
      <div
        className={`pal-row ${confirmDelete ? 'pal-row--confirm' : ''} ${dragging ? 'dragging' : ''}`}
        draggable={!palette.is_default}
        onDragStart={handleDragStart}
        onDragEnd={() => setDragging(false)}
      >
        {!palette.is_default && (
          <div className="pal-drag-handle"><GripVertical size={12} /></div>
        )}
        <div className="pal-row-info">
          {renaming ? (
            <input
              className="pal-row-name-input"
              value={renameVal}
              onChange={e => setRenameVal(e.target.value)}
              onBlur={commitRename}
              onKeyDown={e => {
                if (e.key === 'Enter') commitRename()
                if (e.key === 'Escape') { setRenameVal(displayName); setRenaming(false) }
              }}
              onClick={e => e.stopPropagation()}
              autoFocus
            />
          ) : (
            <span
              className={`pal-row-name ${!palette.is_default ? 'editable' : ''}`}
              title={palette.is_default ? palette.name : 'click to rename'}
              onClick={() => !palette.is_default && setRenaming(true)}
            >
              {displayName}
            </span>
          )}
          <span className="pal-row-count">{palette.count} colors</span>
        </div>
        <div className="pal-row-strip">
          <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
        </div>
        <div className="pal-row-actions">
          {!palette.is_default && (
            <button className="pal-icon-btn" title="edit colors" onClick={() => setEditing(e => !e)}>
              <Palette size={12} />
            </button>
          )}
          {!palette.is_default && (
            <MoveDropdown
              folders={folders}
              currentFolder={palette.folder ?? null}
              onMove={targetFolder => onMove(palPath, targetFolder)}
            />
          )}
          <button className="pal-icon-btn" title="download .pal" onClick={() => onDownload(palPath)}>
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

      {editing && !palette.is_default && (
        <ColorEditor
          palette={{ ...palette, path: palPath }}
          onSave={newColors => { setEditing(false); onColorsUpdated(palPath, newColors) }}
          onCancel={() => setEditing(false)}
        />
      )}
    </>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Folder section (user palettes, with drag-to-move support)
// ─────────────────────────────────────────────────────────────────────────────

function FolderSection({ folderName, label, palettes, folders, allFolders, onPaletteAction, onDeleteFolder, onDropPalette }) {
  const [open, setOpen]       = useState(true)
  const [dragOver, setDragOver] = useState(false)

  const handleDragOver = e => {
    if (!e.dataTransfer.types.includes('text/plain')) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(true)
  }
  const handleDragLeave = e => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragOver(false)
  }
  const handleDrop = e => {
    e.preventDefault()
    setDragOver(false)
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (!data.palettePath) return
      if (data.folder !== (folderName ?? null)) {
        onDropPalette(data.palettePath, folderName ?? null)
      }
    } catch { /* ignore */ }
  }

  return (
    <div
      className={`pal-folder-section ${dragOver ? 'drag-over' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="pal-folder-header">
        <button className="pal-folder-collapse-btn" onClick={() => setOpen(o => !o)}>
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>
        <span className="pal-folder-icon">
          {open ? <FolderOpen size={13} /> : <Folder size={13} />}
        </span>
        <span className="pal-folder-name">
          {label.includes('/') ? (
            <>
              <span style={{ opacity: 0.5 }}>{label.slice(0, label.lastIndexOf('/') + 1)}</span>
              <span className="path-leaf">{label.slice(label.lastIndexOf('/') + 1)}</span>
            </>
          ) : (
            <span className="path-leaf">{label}</span>
          )}
        </span>
        <span className="pal-folder-count">{palettes.length}</span>
        {folderName && (
          <div className="pal-folder-actions">
            <button
              className="pal-folder-action-btn danger"
              title={palettes.length > 0 ? 'move all palettes out first' : 'delete folder'}
              onClick={() => onDeleteFolder(folderName)}
              disabled={palettes.length > 0}
            >
              <Trash2 size={11} />
            </button>
          </div>
        )}
      </div>

      {open && (
        <div className="pal-folder-body">
          {palettes.map(p => (
            <PaletteRow
              key={p.path}
              palette={p}
              folders={allFolders}
              onDelete={onPaletteAction.delete}
              onDownload={onPaletteAction.download}
              onRename={onPaletteAction.rename}
              onMove={onPaletteAction.move}
              onColorsUpdated={onPaletteAction.colorsUpdated}
            />
          ))}
          {palettes.length === 0 && (
            <p style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', padding: '8px 4px' }}>
              empty folder — drag palettes here
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// New folder modal
// ─────────────────────────────────────────────────────────────────────────────

function NewFolderModal({ onClose, onCreate }) {
  const [name, setName]   = useState('')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleCreate = async () => {
    const n = name.trim()
    if (!n) return
    setSaving(true); setError(null)
    try {
      const res = await fetch(`${API}/palettes/folders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: n }),
      })
      if (!res.ok) { const t = await res.text(); throw new Error(t) }
      onCreate(n)
      onClose()
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <Modal title="new folder" onClose={onClose} size="sm">
      <div className="palettes-new-folder-form">
        <div className="field">
          <label className="field-label">folder name</label>
          <input
            className="field-input"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCreate() }}
            placeholder="e.g. starters"
            autoFocus
            spellCheck={false}
          />
        </div>
        {error && <p className="error-msg">{error}</p>}
        <button className="btn-primary" disabled={!name.trim() || saving} onClick={handleCreate}>
          {saving ? 'creating…' : 'create folder'}
        </button>
      </div>
    </Modal>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main tab
// ─────────────────────────────────────────────────────────────────────────────

export function PalettesTab() {
  const [palettes, setPalettes]             = useState([])
  const [knownFolders, setKnownFolders]     = useState([])
  const [loading, setLoading]               = useState(false)
  const [reloading, setReloading]           = useState(false)
  const [error, setError]                   = useState(null)
  const [showLibrary, setShowLibrary]       = useState(false)
  const [showNewFolder, setShowNewFolder]   = useState(false)
  const fileRef = useRef()

  const fetchPalettes = async () => {
    setLoading(true)
    try {
      const [palData, folderData] = await Promise.all([
        fetch(`${API}/palettes`).then(r => r.json()),
        fetch(`${API}/palettes/folders`).then(r => r.json()),
      ])
      setPalettes(palData)
      setKnownFolders(folderData)
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

  const handleDelete = async (path) => {
    const res = await fetch(`${API}/palettes/${encodeURIComponent(path)}`, { method: 'DELETE' })
    if (!res.ok) { setError(await res.text()); return }
    await fetchPalettes()
  }

  const handleDownload = (path) => {
    const a = document.createElement('a')
    a.href = `${API}/palettes/${encodeURIComponent(path)}/download`
    a.download = path.includes('/') ? path.split('/').pop() : path
    a.click()
  }

  const handleRename = async (path, newStem) => {
    const res = await fetch(`${API}/palettes/${encodeURIComponent(path)}/rename`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_name: newStem }),
    })
    if (!res.ok) { setError(await res.text()); return }
    await fetchPalettes()
  }

  const handleMove = async (path, targetFolder) => {
    const res = await fetch(`${API}/palettes/${encodeURIComponent(path)}/move`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_folder: targetFolder }),
    })
    if (!res.ok) { setError(await res.text()); return }
    await fetchPalettes()
  }

  const handleColorsUpdated = async () => {
    await fetchPalettes()
  }

  const handleDeleteFolder = async (name) => {
    const res = await fetch(`${API}/palettes/folders/${encodeURIComponent(name)}`, { method: 'DELETE' })
    if (!res.ok) { setError(await res.text()); return }
    await fetchPalettes()
  }

  const paletteActions = {
    delete:        handleDelete,
    download:      handleDownload,
    rename:        handleRename,
    move:          handleMove,
    colorsUpdated: handleColorsUpdated,
  }

  // Group palettes by source → folder
  const grouped = {}
  for (const p of palettes) {
    const src = p.source
    if (!grouped[src]) grouped[src] = {}
    const folderKey = p.folder ?? '__root__'
    if (!grouped[src][folderKey]) grouped[src][folderKey] = []
    grouped[src][folderKey].push(p)
  }

  const userFolders = [...new Set([
    ...palettes.filter(p => p.source === 'user' && p.folder).map(p => p.folder),
    ...knownFolders,
  ])].sort()

  const defaultPalettes  = grouped['default']?.['__root__'] ?? []
  const legacyPalettes   = grouped['legacy']?.['__root__']  ?? []
  const userRoot         = grouped['user']?.['__root__']    ?? []
  const userFolderGroups = userFolders.map(f => ({
    name:     f,
    palettes: grouped['user']?.[f] ?? [],
  }))

  return (
    <div className="tab-content">
      {showLibrary && (
        <LibraryDrawer onClose={() => setShowLibrary(false)} onImport={fetchPalettes} />
      )}
      {showNewFolder && (
        <NewFolderModal
          onClose={() => setShowNewFolder(false)}
          onCreate={() => fetchPalettes()}
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
              <span className="palettes-stat-num">{palettes.filter(p => p.source === 'default').length}</span>
              <span className="palettes-stat-label">defaults</span>
            </div>
            <div className="palettes-stat-item">
              <span className="palettes-stat-num">{palettes.filter(p => p.source === 'user').length}</span>
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
              ref={fileRef} type="file" accept=".pal" multiple
              style={{ display: 'none' }}
              onChange={e => { handleUpload(e.target.files); e.target.value = '' }}
            />
            <button className="btn-secondary" onClick={handleReload} disabled={reloading}>
              <RefreshCw size={12} className={reloading ? 'spinning' : ''} /> reload
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}

          <div className="palettes-left-hint">
            <p>Palettes are used in Convert and Batch tabs.</p>
            <p>Put <code>.pal</code> files in <code>palettes/user/</code> or subfolders.</p>
            <p>Files in <code>palettes/defaults/</code> are read-only.</p>
            <p>Click a palette name to rename it. Click <Palette size={9} style={{ display: 'inline' }} /> to edit colors.</p>
          </div>
        </div>

        {/* ── Right panel ── */}
        <div className="palettes-right">
          <div className="palettes-toolbar">
            <span className="section-label">loaded palettes</span>
            <div className="palettes-toolbar-right">
              <button className="palettes-new-folder-btn" onClick={() => setShowNewFolder(true)}>
                <FolderPlus size={12} /> new folder
              </button>
            </div>
          </div>

          {loading && <div className="empty-state"><div className="spinner" /></div>}

          {!loading && palettes.length === 0 && (
            <div className="empty-state">
              <p>no palettes loaded — browse the library or upload <code>.pal</code> files</p>
            </div>
          )}

          {/* Defaults — flat read-only list */}
          {!loading && defaultPalettes.length > 0 && (
            <FolderSection
              folderName={null}
              label="palettes/defaults"
              palettes={defaultPalettes.map(p => ({ ...p, is_default: true }))}
              folders={[]}
              allFolders={userFolders}
              onPaletteAction={paletteActions}
              onDeleteFolder={() => {}}
              onDropPalette={() => {}}
            />
          )}

          {/* User palettes — root + subfolders, with drag-to-move */}
          {!loading && (
            <>
              <FolderSection
                folderName={null}
                label="palettes/user"
                palettes={userRoot}
                folders={userFolders}
                allFolders={userFolders}
                onPaletteAction={paletteActions}
                onDeleteFolder={handleDeleteFolder}
                onDropPalette={(palPath, targetFolder) => handleMove(palPath, targetFolder)}
              />
              {userFolderGroups.map(fg => (
                <FolderSection
                  key={fg.name}
                  folderName={fg.name}
                  label={`palettes/user/${fg.name}`}
                  palettes={fg.palettes}
                  folders={userFolders}
                  allFolders={userFolders}
                  onPaletteAction={paletteActions}
                  onDeleteFolder={handleDeleteFolder}
                  onDropPalette={(palPath, targetFolder) => handleMove(palPath, targetFolder)}
                />
              ))}
            </>
          )}

          {/* Legacy */}
          {!loading && legacyPalettes.length > 0 && (
            <div className="palettes-group">
              <div className="palettes-group-header">
                <span className="section-label">other</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 10, padding: '1px 7px' }}>
                  {legacyPalettes.length}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {legacyPalettes.map(p => (
                  <PaletteRow
                    key={p.path}
                    palette={p}
                    folders={userFolders}
                    onDelete={handleDelete}
                    onDownload={handleDownload}
                    onRename={handleRename}
                    onMove={handleMove}
                    onColorsUpdated={handleColorsUpdated}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}