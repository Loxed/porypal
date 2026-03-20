/**
 * frontend/src/components/TrainerCard.jsx
 *
 * Displays trainers from graphics/trainers/ which has this structure:
 *   front_pics/brendan.png
 *   back_pics/brendan.png   (optional, only a handful exist)
 *   palettes/brendan.pal    (optional)
 *
 * Each trainer gets one row: front | back (if exists) | name | palette strip | actions
 * Unmatched palettes (no front_pic) are shown below as plain palette rows.
 */

import { useState } from 'react'
import { Check, Download, FolderInput, Loader, Wand2, X } from 'lucide-react'
import { PaletteStrip } from '../PaletteStrip'
import './TrainerCard.css'

const API = '/api'

// ── Sprite thumb ──────────────────────────────────────────────────────────

function Thumb({ path, label, small = false }) {
  const [err, setErr] = useState(false)
  return (
    <div className={`tc-thumb ${small ? 'tc-thumb--small' : ''}`} title={label}>
      {path && !err
        ? <img
            className="tc-img"
            src={`${API}/palette-library/sprite?path=${encodeURIComponent(path)}`}
            alt={label}
            draggable={false}
            onError={() => setErr(true)}
          />
        : <div className="tc-img-missing" />
      }
    </div>
  )
}

// ── Import button ─────────────────────────────────────────────────────────

function ImportBtn({ palPath, onImport }) {
  const [state, setState] = useState('idle')

  const handle = async () => {
    if (state !== 'idle') return
    setState('loading')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: palPath }),
      })
      if (!res.ok) throw new Error()
      setState('done')
      onImport?.()
      setTimeout(() => setState('idle'), 2000)
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 2000)
    }
  }

  return (
    <button
      className={`tc-btn ${state === 'done' ? 'tc-btn--done' : state === 'error' ? 'tc-btn--error' : ''}`}
      onClick={handle}
      disabled={state === 'loading'}
      title="Import to Porypal"
    >
      {state === 'done'    ? <Check size={11} />
      : state === 'error'  ? <X size={11} />
      : state === 'loading'? <Loader size={11} className="tc-spin" />
      : <FolderInput size={11} />}
    </button>
  )
}

// ── Generate palette button ──────────────────────────────────────────────

function GenerateBtn({ spritePath, expectedPalPath, onGenerated }) {
  const [state, setState] = useState('idle')

  const handle = async () => {
    if (state !== 'idle') return
    setState('loading')
    try {
      const res = await fetch(`${API}/palette-library/items/generate-palette`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sprite_path:           spritePath,
          expected_palette_path: expectedPalPath,
          n_colors: 15,
          bg_color: '#73C5A4',
        }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      onGenerated({ path: data.palette_path, colors: data.colors })
      setState('idle')
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 2000)
    }
  }

  return (
    <button
      className={`tc-btn ${state === 'error' ? 'tc-btn--error' : ''}`}
      onClick={handle}
      disabled={state === 'loading'}
      title="Auto-generate palette from sprite"
    >
      {state === 'loading' ? <Loader size={11} className="tc-spin" />
      : state === 'error'  ? <X size={11} />
      : <Wand2 size={11} />}
    </button>
  )
}

// ── Single trainer row ────────────────────────────────────────────────────

function TrainerRow({ name, frontPath, backPath, palette: initialPalette, onImport, expectedPalPath }) {
  const [palette, setPalette] = useState(initialPalette)

  return (
    <div className="tc-row">
      {/* Front pic */}
      <Thumb path={frontPath} label={`${name} front`} />

      {/* Back pic — always reserve space so rows align */}
      <div className="tc-back-slot">
        {backPath
          ? <Thumb path={backPath} label={`${name} back`} small />
          : <div className="tc-back-empty" title="no back pic" />
        }
      </div>

      {/* Name */}
      <span className="tc-name" title={name}>{name}</span>

      {/* Palette strip or hint */}
      {palette
        ? <div className="tc-strip">
            <PaletteStrip
              colors={palette.colors}
              usedIndices={palette.colors.map((_, i) => i)}
              checkSize="50%"
            />
          </div>
        : <span className="tc-no-pal">no palette</span>
      }

      {/* Generate — only when no palette and we have a front pic to extract from */}
      {!palette && frontPath && (
        <GenerateBtn
          spritePath={frontPath}
          expectedPalPath={expectedPalPath}
          onGenerated={setPalette}
        />
      )}

      {/* Download + Import — only when palette exists */}
      {palette && (
        <>
          <a
            className="tc-btn"
            href={`${API}/palette-library/sprite?path=${encodeURIComponent(palette.path)}`}
            download={`${name}.pal`}
            title="Download .pal"
          >
            <Download size={11} />
          </a>
          <ImportBtn palPath={palette.path} onImport={onImport} />
        </>
      )}
    </div>
  )
}

// ── Lone palette row (no matching sprite) ─────────────────────────────────

function LoosePaletteRow({ name, palette, onImport }) {
  return (
    <div className="tc-row tc-row--loose">
      <div className="tc-thumb tc-thumb--empty" />
      <div className="tc-back-slot"><div className="tc-back-empty" /></div>
      <span className="tc-name tc-name--muted" title={name}>{name}</span>
      <div className="tc-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
      <a
        className="tc-btn"
        href={`${API}/palette-library/sprite?path=${encodeURIComponent(palette.path)}`}
        download={`${name}.pal`}
        title="Download .pal"
      >
        <Download size={11} />
      </a>
      <ImportBtn palPath={palette.path} onImport={onImport} />
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────

/**
 * Props:
 *   nodes    — flat array of {type, name, path, colors?} from the library API
 *              representing the contents of the trainers/ folder
 *   onImport — callback after a palette is imported
 *
 * The nodes come from walking the trainers/ folder which contains:
 *   front_pics/*.png, back_pics/*.png, palettes/*.pal
 * These arrive as child nodes of sub-folders (front_pics, back_pics, palettes).
 * We receive the top-level folder's children which are folder nodes,
 * so this component receives the already-fetched flat children list.
 */
export function TrainerCard({ nodes, onImport, query = '' }) {
  if (!nodes?.length) return null

  // Separate into maps by type
  const frontMap   = new Map()  // stem → path
  const backMap    = new Map()  // stem → path
  const paletteMap = new Map()  // stem → {path, colors}

  for (const node of nodes) {
    if (node.type === 'folder') continue

    // name may be missing — fall back to the last path segment
    const filename = node.name ?? node.path.replace(/\\/g, '/').split('/').pop() ?? ''
    if (!filename) continue
    const ext  = filename.split('.').pop().toLowerCase()
    const stem = filename.replace(/\.[^.]+$/, '')

    // Use _subfolder tag (set by TrainerFolderSection) for reliable categorisation
    const subfolder = (node._subfolder ?? '').toLowerCase()
    if (ext === 'png') {
      if (subfolder === 'back_pics') {
        backMap.set(stem, node.path)
      } else {
        // front_pics or root-level
        frontMap.set(stem, node.path)
      }
    } else if (ext === 'pal' && node.colors) {
      paletteMap.set(stem, { path: node.path, colors: node.colors })
    }
  }

  // Derive the palettes/ sub-folder prefix from any palette node path
  // e.g. "pokeemerald/trainers/palettes/brendan.pal" → "pokeemerald/trainers/palettes"
  let palettesPrefix = null
  for (const [, pal] of paletteMap) {
    const parts = pal.path.replace(/\\/g, '/').split('/')
    if (parts.length > 1) { palettesPrefix = parts.slice(0, -1).join('/'); break }
  }
  // If no palette exists yet, derive from any front_pics path
  if (!palettesPrefix) {
    for (const [, fp] of frontMap) {
      const parts = fp.replace(/\\/g, '/').split('/')
      // replace "front_pics" segment with "palettes"
      const idx = parts.findIndex(p => p === 'front_pics')
      if (idx !== -1) { parts[idx] = 'palettes'; palettesPrefix = parts.slice(0, -1).join('/'); break }
    }
  }

  // Build trainer list: everyone with a front pic
  const trainers = []
  const handledPals = new Set()

  for (const [stem, frontPath] of frontMap) {
    const palette = paletteMap.get(stem) ?? null
    if (palette) handledPals.add(stem)
    trainers.push({ stem, frontPath, backPath: backMap.get(stem) ?? null, palette, palettesPrefix })
  }

  // Also include back-pic-only entries (very rare)
  for (const [stem, backPath] of backMap) {
    if (frontMap.has(stem)) continue
    const palette = paletteMap.get(stem) ?? null
    if (palette) handledPals.add(stem)
    trainers.push({ stem, frontPath: null, backPath, palette, palettesPrefix })
  }

  // Unmatched palettes
  const loosePalettes = []
  for (const [stem, palette] of paletteMap) {
    if (!handledPals.has(stem)) {
      loosePalettes.push({ stem, palette })
    }
  }

  trainers.sort((a, b) => a.stem.localeCompare(b.stem))
  loosePalettes.sort((a, b) => a.stem.localeCompare(b.stem))

  const q = query.trim().toLowerCase()
  const visibleTrainers = q ? trainers.filter(t => t.stem.toLowerCase().includes(q)) : trainers
  const visibleLoose    = q ? loosePalettes.filter(t => t.stem.toLowerCase().includes(q)) : loosePalettes

  return (
    <div className="tc-list">
      {visibleTrainers.map(({ stem, frontPath, backPath, palette, palettesPrefix }) => (
        <TrainerRow
          key={stem}
          name={stem}
          frontPath={frontPath}
          backPath={backPath}
          palette={palette}
          onImport={onImport}
          expectedPalPath={palettesPrefix ? `${palettesPrefix}/${stem}.pal` : null}
        />
      ))}

      {visibleLoose.length > 0 && (
        <>
          {visibleTrainers.length > 0 && <div className="tc-divider" />}
          {visibleLoose.map(({ stem, palette }) => (
            <LoosePaletteRow key={stem} name={stem} palette={palette} onImport={onImport} />
          ))}
        </>
      )}
    </div>
  )
}