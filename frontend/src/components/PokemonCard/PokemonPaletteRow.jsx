import { useState } from 'react'
import { Check, Download } from 'lucide-react'
import { PaletteStrip } from '../PaletteStrip'

const API = '/api'

// Well-known palette filename → display label
export const PAL_LABELS = {
  'normal.pal':           'normal',
  'shiny.pal':            'shiny',
  'overworld_normal.pal': 'ow normal',
  'overworld_shiny.pal':  'ow shiny',
}

export function PokemonPaletteRow({ palette, label, onImport }) {
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
      onImport?.()
      setTimeout(() => setImportState('idle'), 2000)
    } catch {
      setImportState('error')
      setTimeout(() => setImportState('idle'), 2000)
    }
  }

  return (
    <div className="pkm-pal-row">
      <span className="pkm-pal-label">{label ?? palette.name.replace(/\.pal$/, '')}</span>
      <div className="pkm-pal-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
      <button
        className={`lib-import-btn pkm-import-btn ${importState}`}
        onClick={handleImport}
        disabled={importState === 'importing'}
        title={`import ${palette.name}`}
      >
        {importState === 'done'
          ? <Check size={11} />
          : importState === 'error'
          ? '!'
          : <Download size={11} />
        }
      </button>
    </div>
  )
}