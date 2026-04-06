/**
 * frontend/src/components/PalettePicker.jsx
 *
 * Shared palette picker used across Convert, Shiny, Variants (apply), and Batch tabs.
 *
 * Props:
 *   palettes        [{name, folder, colors, ...}]  full palette list from /api/palettes
 *   mode            'multi' | 'single'
 *   selected        Set<string> (multi) | string | null (single)
 *   onChange        (newSelected) => void
 *                     multi: receives new Set<string>
 *                     single: receives name string or null
 *   onImportFile    optional: (File) => void  — called when user imports a .pal file
 *   allowMultiImport bool — allow selecting/importing multiple .pal files at once
 *   compact         bool — smaller max-height, tighter layout
 *   showSelectAll   bool — show select/deselect all button (multi only, default true)
 *   placeholder     string — search placeholder
 */

import { useState, useRef, useMemo } from 'react'
import { ChevronDown, ChevronRight, Upload, Check } from 'lucide-react'
import { PaletteStrip } from './PaletteStrip'
import './PalettePicker.css'

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

// ── FolderSection ────────────────────────────────────────────────────────────

function FolderSection({ folderName, palettes, mode, selected, onChange }) {
  const [open, setOpen] = useState(true)
  if (palettes.length === 0) return null

  return (
    <div className="pal-picker-folder">
      <button className="pal-picker-folder-header" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <span className="pal-picker-folder-name">{folderName}</span>
        <span className="pal-picker-folder-count">{palettes.length}</span>
      </button>
      {open && (
        <div className="pal-picker-folder-body">
          {palettes.map(p => (
            <PaletteRow key={p.name} palette={p} mode={mode} selected={selected} onChange={onChange} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── PaletteRow ───────────────────────────────────────────────────────────────

function PaletteRow({ palette, mode, selected, onChange }) {
  const isActive = mode === 'multi'
    ? selected instanceof Set && selected.has(palette.name)
    : selected === palette.name

  const handleClick = () => {
    if (mode === 'multi') {
      const next = new Set(selected)
      isActive ? next.delete(palette.name) : next.add(palette.name)
      onChange(next)
    } else {
      onChange(isActive ? null : palette.name)
    }
  }

  // Strip the folder prefix for display
  const displayName = palette.name.includes('/')
    ? palette.name.split('/').pop().replace(/\.pal$/, '')
    : palette.name.replace(/\.pal$/, '')

  return (
    <div className={`pal-picker-row ${isActive ? 'active' : ''}`} onClick={handleClick}>
      {mode === 'multi'
        ? <input type="checkbox" className="pal-picker-check" checked={isActive} readOnly onClick={e => e.stopPropagation()} />
        : <input type="radio" className="pal-picker-radio" checked={isActive} readOnly onClick={e => e.stopPropagation()} />
      }
      <span className="pal-picker-name" title={palette.name}>{displayName}</span>
      <div className="pal-picker-strip-wrap">
        <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
      </div>
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────────────────────────

export function PalettePicker({
  palettes = [],
  mode = 'multi',
  selected,
  onChange,
  onImportFile,
  allowMultiImport = false,
  compact = false,
  showSelectAll = true,
  placeholder = 'search palettes…',
}) {
  const [search, setSearch] = useState('')
  const fileRef = useRef()

  const handleImport = (e) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length === 0 || !onImportFile) return
    const picked = allowMultiImport ? files : files.slice(0, 1)
    picked.forEach(onImportFile)
    e.target.value = ''
  }

  // Filter + group
  const q = search.trim().toLowerCase()

  const filtered = useMemo(() => {
    if (!q) return palettes
    return palettes.filter(p => {
      const displayName = p.name.replace(/\.pal$/, '').replace('/', ' ')
      return displayName.toLowerCase().includes(q)
    })
  }, [palettes, q])

  // Group into { null: [...], folder1: [...], folder2: [...] }
  const grouped = useMemo(() => {
    const map = {}
    for (const p of filtered) {
      const key = p.folder ?? '__root__'
      if (!map[key]) map[key] = []
      map[key].push(p)
    }
    return map
  }, [filtered])

  const rootPalettes = grouped['__root__'] ?? []
  const folderNames = Object.keys(grouped).filter(k => k !== '__root__').sort()

  // Multi: select all / deselect all
  const allNames = filtered.map(p => p.name)
  const allSelected = mode === 'multi' && allNames.length > 0 && allNames.every(n => selected instanceof Set && selected.has(n))

  const handleSelectAll = () => {
    if (mode !== 'multi') return
    if (allSelected) {
      const next = new Set(selected)
      allNames.forEach(n => next.delete(n))
      onChange(next)
    } else {
      const next = new Set(selected)
      allNames.forEach(n => next.add(n))
      onChange(next)
    }
  }

  const selectedCount = mode === 'multi' ? (selected instanceof Set ? selected.size : 0) : 0

  return (
    <div className={`pal-picker ${compact ? 'compact' : ''}`}>

      {/* Search */}
      <div className="pal-picker-search-wrap">
        <input
          className="pal-picker-search"
          placeholder={placeholder}
          value={search}
          onChange={e => setSearch(e.target.value)}
          spellCheck={false}
        />
        {search && (
          <button className="pal-picker-search-clear" onClick={() => setSearch('')}>✕</button>
        )}
      </div>

      {/* Actions row */}
      <div className="pal-picker-actions">
        {onImportFile && (
          <>
            <button className="pal-picker-import-btn" onClick={() => fileRef.current?.click()}>
              <Upload size={10} /> {allowMultiImport ? 'import .pal files' : 'import .pal'}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".pal"
              multiple={allowMultiImport}
              style={{ display: 'none' }}
              onChange={handleImport}
            />
          </>
        )}
        {mode === 'multi' && showSelectAll && palettes.length > 0 && (
          <button className="pal-picker-select-all" onClick={handleSelectAll}>
            {allSelected ? 'deselect all' : 'select all'}
          </button>
        )}
        {mode === 'multi' && (
          <span className="pal-picker-count">{selectedCount}/{palettes.length}</span>
        )}
      </div>

      {/* List */}
      <div className="pal-picker-list">
        {filtered.length === 0 && (
          <div className="pal-picker-empty">
            {palettes.length === 0
              ? <><p>No palettes loaded.</p><p>Upload <code>.pal</code> files or browse the library.</p></>
              : <p>No palettes match "{search}"</p>
            }
          </div>
        )}

        {/* Root palettes */}
        {rootPalettes.map(p => (
          <PaletteRow key={p.name} palette={p} mode={mode} selected={selected} onChange={onChange} />
        ))}

        {/* Folder sections */}
        {folderNames.map(folder => (
          <FolderSection
            key={folder}
            folderName={folder}
            palettes={grouped[folder]}
            mode={mode}
            selected={selected}
            onChange={onChange}
          />
        ))}
      </div>
    </div>
  )
}
