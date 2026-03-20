/**
 * frontend/src/components/LibraryItemCard.jsx
 *
 * One item row: sprite + name + palette strip + actions.
 * If no palette exists, shows a "generate" button that calls the extract API
 * and updates the card in place.
 */

import { useState } from 'react'
import { Check, Download, FolderInput, Loader, X, Wand2 } from 'lucide-react'
import { PaletteStrip } from '../PaletteStrip'
import './LibraryItemCard.css'

const API = '/api'

export function LibraryItemCard({ item, onImport }) {
  const [palette, setPalette]     = useState(
    item.colors ? { path: item.palette_path, colors: item.colors } : null
  )
  const [importState, setImport]  = useState('idle')
  const [genState, setGen]        = useState('idle')   // idle | loading | error
  const [imgError, setImgError]   = useState(false)

  const hasPalette = palette !== null

  // -- Generate palette ----------------------------------------------------
  const handleGenerate = async () => {
    if (genState !== 'idle') return
    setGen('loading')
    try {
      const res = await fetch(`${API}/palette-library/items/generate-palette`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sprite_path:           item.sprite_path,
          expected_palette_path: item.expected_palette_path,
          n_colors: 15,
          bg_color: '#73C5A4',
        }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setPalette({ path: data.palette_path, colors: data.colors })
      setGen('idle')
    } catch {
      setGen('error')
      setTimeout(() => setGen('idle'), 2000)
    }
  }

  // -- Import palette to palettes/user/ -----------------------------------
  const handleImport = async () => {
    if (!hasPalette || importState !== 'idle') return
    setImport('loading')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: palette.path }),
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
    <div className="lib-item-card">

      {/* Sprite */}
      <div className="lib-item-card-thumb">
        {item.sprite_path && !imgError
          ? <img
              className="lib-item-card-img"
              src={`${API}/palette-library/sprite?path=${encodeURIComponent(item.sprite_path)}`}
              alt={item.name}
              draggable={false}
              onError={() => setImgError(true)}
            />
          : <div className="lib-item-card-img-missing" />
        }
      </div>

      {/* Name */}
      <span className="lib-item-card-name" title={item.name}>{item.name}</span>

      {/* Palette strip or "no palette" hint */}
      <div className="lib-item-card-strip">
        {hasPalette
          ? <PaletteStrip colors={palette.colors} usedIndices={palette.colors.map((_, i) => i)} checkSize="50%" />
          : <span className="lib-item-card-no-pal">no palette</span>
        }
      </div>

      {/* Generate button - only shown when no palette */}
      {!hasPalette && (
        <button
          className={`lib-item-card-btn ${genState === 'error' ? 'lib-item-card-btn--error' : 'lib-item-card-btn--generate'}`}
          onClick={handleGenerate}
          disabled={genState === 'loading'}
          title="Auto-generate palette from sprite"
        >
          {genState === 'loading' ? <Loader size={11} className="lib-item-card-spin" />
           : genState === 'error' ? <X size={11} />
           : <Wand2 size={11} />}
        </button>
      )}

      {/* Download - only when palette exists */}
      {hasPalette && (
        <a
          className="lib-item-card-btn"
          href={`${API}/palette-library/sprite?path=${encodeURIComponent(palette.path)}`}
          download={`${item.name}.pal`}
          title="Download .pal"
        >
          <Download size={11} />
        </a>
      )}

      {/* Import to palettes/user/ */}
      <button
        className={`lib-item-card-btn ${!hasPalette ? 'lib-item-card-btn--disabled' : ''} ${importState === 'done' ? 'lib-item-card-btn--done' : importState === 'error' ? 'lib-item-card-btn--error' : ''}`}
        onClick={handleImport}
        disabled={!hasPalette || importState === 'loading'}
        title={hasPalette ? 'Import to Porypal' : 'Generate a palette first'}
      >
        {importState === 'done'    ? <Check size={11} />
        : importState === 'error'  ? <X size={11} />
        : importState === 'loading'? <Loader size={11} className="lib-item-card-spin" />
        : <FolderInput size={11} />}
      </button>

    </div>
  )
}