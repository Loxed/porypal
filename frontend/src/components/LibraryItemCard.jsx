/**
 * frontend/src/components/LibraryItemCard.jsx
 *
 * Displays one item: sprite preview + palette strip + import/download actions.
 * Used inside LibraryDrawer's ItemsFolderSection.
 *
 * Data shape (from /api/palette-library/items):
 *   { name, sprite_path, palette_path | null, colors | null }
 */

import { useState } from 'react'
import { Check, Download, FolderInput, Loader, X } from 'lucide-react'
import { PaletteStrip } from './PaletteStrip'
import './LibraryItemCard.css'

const API = '/api'

export function LibraryItemCard({ item, onImport }) {
  const [importState, setImportState] = useState('idle') // idle | loading | done | error
  const [imgError, setImgError]       = useState(false)

  const handleImport = async () => {
    if (!item.palette_path || importState !== 'idle') return
    setImportState('loading')
    try {
      const res = await fetch(`${API}/palette-library/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: item.palette_path }),
      })
      if (!res.ok) throw new Error()
      setImportState('done')
      onImport?.()
      setTimeout(() => setImportState('idle'), 2000)
    } catch {
      setImportState('error')
      setTimeout(() => setImportState('idle'), 2000)
    }
  }

  return (
    <div className="lib-item-card">

      {/* Sprite thumbnail */}
      <div className="lib-item-card-thumb">
        {item.sprite_path && !imgError ? (
          <img
            className="lib-item-card-img"
            src={`${API}/palette-library/sprite?path=${encodeURIComponent(item.sprite_path)}`}
            alt={item.name}
            draggable={false}
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="lib-item-card-img-missing" />
        )}
      </div>

      {/* Name */}
      <span className="lib-item-card-name" title={item.name}>{item.name}</span>

      {/* Palette strip — fills remaining space */}
      <div className="lib-item-card-strip">
        {item.colors ? (
          <PaletteStrip
            colors={item.colors}
            usedIndices={item.colors.map((_, i) => i)}
            checkSize="50%"
          />
        ) : (
          <span className="lib-item-card-no-pal">no palette</span>
        )}
      </div>

      {/* Actions */}
      {item.palette_path && (
        <a
          className="lib-item-card-btn"
          href={`${API}/palette-library/sprite?path=${encodeURIComponent(item.palette_path)}`}
          download={`${item.name}.pal`}
          title="Download .pal"
        >
          <Download size={11} />
        </a>
      )}

      <button
        className={`lib-item-card-btn ${!item.palette_path ? 'lib-item-card-btn--disabled' : ''} ${importState === 'done' ? 'lib-item-card-btn--done' : importState === 'error' ? 'lib-item-card-btn--error' : ''}`}
        onClick={handleImport}
        disabled={!item.palette_path || importState === 'loading'}
        title={item.palette_path ? 'Import palette to Porypal' : 'No palette available'}
      >
        {importState === 'done'    ? <Check size={11} />
        : importState === 'error'  ? <X size={11} />
        : importState === 'loading'? <Loader size={11} className="lib-item-card-spin" />
        : <FolderInput size={11} />}
      </button>

    </div>
  )
}