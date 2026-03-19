import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { PokemonSprite } from './PokemonSprite'
import { PokemonPaletteRow, PAL_LABELS } from './PokemonPaletteRow'

// Sprite filenames to try for the form header icon (in priority order)
const ICON_PRIORITY = ['icon.png', 'front.png', 'anim_front.png', 'anim_frontf.png']

// Sorted order for known palette types
const PAL_ORDER = Object.keys(PAL_LABELS)

export function PokemonFormSection({ node, label, onImport, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)

  const icon  = node.sprites?.find(s => ICON_PRIORITY.includes(s.name.toLowerCase()))
  const front = node.sprites?.find(s => ['front.png', 'anim_front.png'].includes(s.name.toLowerCase()))
  const back  = node.sprites?.find(s => s.name.toLowerCase() === 'back.png')

  // Known palettes first (in order), then any others
  const palettes = [
    ...PAL_ORDER
      .map(name => node.palettes?.find(p => p.name.toLowerCase() === name))
      .filter(Boolean),
    ...(node.palettes?.filter(p => !PAL_ORDER.includes(p.name.toLowerCase())) ?? []),
  ]

  if (palettes.length === 0) return null

  return (
    <div className="pkm-form-section">
      <button className="pkm-form-header" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {icon && <PokemonSprite path={icon.path} className="pkm-form-icon" />}
        <span className="pkm-form-label">{label}</span>
        <span className="pkm-form-count">{palettes.length} pal{palettes.length !== 1 ? 's' : ''}</span>
      </button>

      {open && (
        <div className="pkm-form-body">
          {(front || back) && (
            <div className="pkm-sprites-row">
              {front && <PokemonSprite path={front.path} className="pkm-sprite-front" />}
              {back  && <PokemonSprite path={back.path}  className="pkm-sprite-back"  />}
            </div>
          )}
          <div className="pkm-palettes">
            {palettes.map((pal, i) => (
              <PokemonPaletteRow
                key={i}
                palette={pal}
                label={PAL_LABELS[pal.name.toLowerCase()] ?? pal.name.replace(/\.pal$/, '')}
                onImport={onImport}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}