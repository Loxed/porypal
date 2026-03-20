/**
 * frontend/src/components/GenericFolderCard.jsx
 *
 * Simple card for a non-smart folder in the library drawer.
 * Pairs .png files with matching .pal files by stem name.
 * Shows unmatched files separately.
 */

import { useState } from 'react'
import { Check, Download, FolderInput, Loader, X } from 'lucide-react'
import { PaletteStrip } from '../PaletteStrip'
import './GenericFolderCard.css'

const API = '/api'

// ── Paired: sprite + palette ──────────────────────────────────────────────

function PairedRow({ name, spritePath, palette, onImport }) {
  const [imgErr, setImgErr]     = useState(false)
  const [importState, setImport] = useState('idle')

  const handleImport = async () => {
    if (importState !== 'idle') return
    setImport('loading')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ path: palette.path }),
      })
      if (!res.ok) throw new Error()
      setImport('done')
      onImport?.()
      setTimeout(() => setImport('idle'), 2000)
    } catch {
      setImport('error')
      setTimeout(() => setImport('idle'), 2000)
    }
  }

  return (
    <div className="gfc-row gfc-row--paired">
      {/* Sprite thumb */}
      <div className="gfc-thumb">
        {spritePath && !imgErr
          ? <img
              className="gfc-img"
              src={`${API}/palette-library/sprite?path=${encodeURIComponent(spritePath)}`}
              alt={name}
              draggable={false}
              onError={() => setImgErr(true)}
            />
          : <div className="gfc-img-missing" />
        }
      </div>

      {/* Name */}
      <span className="gfc-name" title={name}>{name}</span>

      {/* Palette strip */}
      <div className="gfc-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>

      {/* Download .pal */}
      <a
        className="gfc-btn"
        href={`${API}/palette-library/sprite?path=${encodeURIComponent(palette.path)}`}
        download={`${name}.pal`}
        title="Download .pal"
      >
        <Download size={11} />
      </a>

      {/* Import to palettes/user/ */}
      <button
        className={`gfc-btn ${importState === 'done' ? 'gfc-btn--done' : importState === 'error' ? 'gfc-btn--error' : ''}`}
        onClick={handleImport}
        disabled={importState === 'loading'}
        title="Import to Porypal"
      >
        {importState === 'done'    ? <Check size={11} />
        : importState === 'error'  ? <X size={11} />
        : importState === 'loading'? <Loader size={11} className="gfc-spin" />
        : <FolderInput size={11} />}
      </button>
    </div>
  )
}

// ── Sprite only ───────────────────────────────────────────────────────────

function SpriteRow({ name, path }) {
  const [imgErr, setImgErr] = useState(false)
  return (
    <div className="gfc-row gfc-row--sprite">
      <div className="gfc-thumb">
        {!imgErr
          ? <img
              className="gfc-img"
              src={`${API}/palette-library/sprite?path=${encodeURIComponent(path)}`}
              alt={name}
              draggable={false}
              onError={() => setImgErr(true)}
            />
          : <div className="gfc-img-missing" />
        }
      </div>
      <span className="gfc-name gfc-name--muted" title={name}>{name}</span>
      <span className="gfc-no-pal">no palette</span>
    </div>
  )
}

// ── Palette only ──────────────────────────────────────────────────────────

function PaletteOnlyRow({ name, palette, onImport }) {
  const [importState, setImport] = useState('idle')

  const handleImport = async () => {
    if (importState !== 'idle') return
    setImport('loading')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ path: palette.path }),
      })
      if (!res.ok) throw new Error()
      setImport('done')
      onImport?.()
      setTimeout(() => setImport('idle'), 2000)
    } catch {
      setImport('error')
      setTimeout(() => setImport('idle'), 2000)
    }
  }

  return (
    <div className="gfc-row gfc-row--palette">
      <div className="gfc-thumb gfc-thumb--empty" />
      <span className="gfc-name" title={name}>{name}</span>
      <div className="gfc-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
      <a
        className="gfc-btn"
        href={`${API}/palette-library/sprite?path=${encodeURIComponent(palette.path)}`}
        download={`${name}.pal`}
        title="Download .pal"
      >
        <Download size={11} />
      </a>
      <button
        className={`gfc-btn ${importState === 'done' ? 'gfc-btn--done' : importState === 'error' ? 'gfc-btn--error' : ''}`}
        onClick={handleImport}
        disabled={importState === 'loading'}
        title="Import to Porypal"
      >
        {importState === 'done'    ? <Check size={11} />
        : importState === 'error'  ? <X size={11} />
        : importState === 'loading'? <Loader size={11} className="gfc-spin" />
        : <FolderInput size={11} />}
      </button>
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────

/**
 * Props:
 *   nodes    — array of {type, name, path, colors?} from the library API
 *   onImport — callback after a palette is imported
 */
export function GenericFolderCard({ nodes, onImport, query = '' }) {
  if (!nodes?.length) return null

  const q = query.trim().toLowerCase()

  // Build lookup maps
  const spriteMap  = new Map()  // stem → path
  const paletteMap = new Map()  // stem → {path, colors}

  for (const node of nodes) {
    if (node.type === 'sprite') {
      const stem = node.name.replace(/\.png$/i, '')
      spriteMap.set(stem, node.path)
    } else if (node.type === 'palette') {
      const stem = node.name.replace(/\.pal$/i, '')
      paletteMap.set(stem, { path: node.path, colors: node.colors })
    }
  }

  // Paired: stem has both
  const paired   = []
  const spriteOnly  = []
  const paletteOnly = []

  const handled = new Set()

  for (const [stem, spritePath] of spriteMap) {
    handled.add(stem)
    if (paletteMap.has(stem)) {
      paired.push({ stem, spritePath, palette: paletteMap.get(stem) })
    } else {
      spriteOnly.push({ stem, spritePath })
    }
  }

  for (const [stem, palette] of paletteMap) {
    if (!handled.has(stem)) {
      paletteOnly.push({ stem, palette })
    }
  }

  // Sort each group alphabetically
  paired.sort((a, b) => a.stem.localeCompare(b.stem))
  spriteOnly.sort((a, b) => a.stem.localeCompare(b.stem))
  paletteOnly.sort((a, b) => a.stem.localeCompare(b.stem))

  // Filter by query if set
  const match = stem => !q || stem.toLowerCase().includes(q)
  const filteredPaired    = q ? paired.filter(r => match(r.stem))    : paired
  const filteredSprite    = q ? spriteOnly.filter(r => match(r.stem)): spriteOnly
  const filteredPaletteOnly = q ? paletteOnly.filter(r => match(r.stem)) : paletteOnly

  if (q && !filteredPaired.length && !filteredSprite.length && !filteredPaletteOnly.length)
    return null

  return (
    <div className="gfc-list">
      {filteredPaired.map(({ stem, spritePath, palette }) => (
        <PairedRow key={stem} name={stem} spritePath={spritePath} palette={palette} onImport={onImport} />
      ))}
      {filteredSprite.map(({ stem, spritePath }) => (
        <SpriteRow key={stem} name={stem} path={spritePath} />
      ))}
      {filteredPaletteOnly.map(({ stem, palette }) => (
        <PaletteOnlyRow key={stem} name={stem} palette={palette} onImport={onImport} />
      ))}
    </div>
  )
}