/**
 * PokemonCard.jsx
 *
 * Displays a collapsed pokemon card. When opened, fetches full node data and shows:
 *  - Sprite pairs (normal + shiny) for: icon, front, back, overworld
 *  - Shiny sprites are generated client-side by remapping with shiny palette colors
 *  - Results are cached at module level so re-opening is instant
 *  - Palette rows with Download + Import buttons
 *
 * Palette mapping:
 *   icon, front, back  →  normal.pal / shiny.pal
 *   overworld          →  overworld_normal.pal / overworld_shiny.pal
 */

import { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight, Loader, Download, FolderInput, Check, X } from 'lucide-react'
import { PaletteStrip } from './PaletteStrip'
import { remapToShinyPalette } from '../utils'
import './PokemonCard.css'

const API = '/api'

// ── Sprite / palette config ───────────────────────────────────────────────────
// Each entry defines: which sprite file to use, and which palette
// names to use for normal / shiny remapping.
const SPRITE_CONFIGS = [
  {
    key: 'icon',
    label: 'Icon',
    sprite: 'icon.png',
    normalPal: 'normal.pal',
    shinyPal: 'shiny.pal',
  },
  {
    key: 'front',
    label: 'Front',
    sprite: 'anim_front.png',
    normalPal: 'normal.pal',
    shinyPal: 'shiny.pal',
  },
  {
    key: 'back',
    label: 'Back',
    sprite: 'back.png',
    normalPal: 'normal.pal',
    shinyPal: 'shiny.pal',
  },
  {
    key: 'ow',
    label: 'OW',
    sprite: 'overworld.png',
    normalPal: 'overworld_normal.pal',
    shinyPal: 'overworld_shiny.pal',
  },
]

// ── Module-level caches ───────────────────────────────────────────────────────
// Persist across component mounts — avoids re-fetching / re-remapping on re-open.
const _rawB64Cache = new Map()      // spritePath → raw base64 PNG
const _remappedCache = new Map()    // `${spritePath}::${cacheKey}` → remapped base64

// ── Helpers ───────────────────────────────────────────────────────────────────

function findPalette(palettes, filename) {
  return palettes?.find(p => p.name.toLowerCase() === filename.toLowerCase()) ?? null
}

function findSprite(sprites, filename) {
  return sprites?.find(s => s.name.toLowerCase() === filename.toLowerCase()) ?? null
}

async function loadSpriteB64(spritePath) {
  if (_rawB64Cache.has(spritePath)) return _rawB64Cache.get(spritePath)
  const res = await fetch(`${API}/palette-library/sprite?path=${encodeURIComponent(spritePath)}`)
  if (!res.ok) throw new Error(`sprite fetch failed: ${res.status}`)
  const blob = await res.blob()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = e => {
      const b64 = e.target.result.split(',')[1]
      _rawB64Cache.set(spritePath, b64)
      resolve(b64)
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

// ── ShinySprite: loads + remaps a sprite with a given palette pair ───────────
function ShinySprite({ spritePath, normalColors, shinyColors, label }) {
  const [state, setState] = useState('idle') // idle | loading | done | error
  const [src, setSrc] = useState(null)

  useEffect(() => {
    if (!spritePath || !normalColors?.length || !shinyColors?.length) return

    const cacheKey = `${spritePath}::${shinyColors.join(',')}`
    if (_remappedCache.has(cacheKey)) {
      setSrc(_remappedCache.get(cacheKey))
      setState('done')
      return
    }

    let cancelled = false
    setState('loading')

    loadSpriteB64(spritePath)
      .then(b64 => remapToShinyPalette(b64, normalColors, shinyColors))
      .then(remapped => {
        if (cancelled) return
        _remappedCache.set(cacheKey, remapped)
        setSrc(remapped)
        setState('done')
      })
      .catch(() => {
        if (!cancelled) setState('error')
      })

    return () => {
      cancelled = true
    }
  }, [spritePath, normalColors, shinyColors])

  if (state === 'error') return <div className="pkm-spr-placeholder" title="failed" />
  if (state !== 'done' || !src) {
    return (
      <div className="pkm-spr-placeholder loading">
        {state === 'loading' && <Loader size={10} className="pkm-spin" />}
      </div>
    )
  }

  return (
    <img
      className="pkm-spr"
      src={`data:image/png;base64,${src}`}
      alt={`${label} shiny`}
      draggable={false}
    />
  )
}

// ── NormalSprite: just shows the raw sprite from disk ────────────────────────
function NormalSprite({ spritePath, label }) {
  const [err, setErr] = useState(false)
  if (!spritePath) return <div className="pkm-spr-placeholder" />
  if (err) return <div className="pkm-spr-placeholder" title="not found" />
  return (
    <img
      className="pkm-spr"
      src={`${API}/palette-library/sprite?path=${encodeURIComponent(spritePath)}`}
      alt={`${label} normal`}
      onError={() => setErr(true)}
      draggable={false}
    />
  )
}

// ── IconSprite: small version for the collapsed card header ──────────────────
function IconSprite({ spritePath }) {
  const [err, setErr] = useState(false)
  if (!spritePath || err) return <div className="pkm-spr-placeholder small" />
  return (
    <img
      className="pkm-spr small"
      src={`${API}/palette-library/sprite?path=${encodeURIComponent(spritePath)}`}
      onError={() => setErr(true)}
      alt=""
      draggable={false}
    />
  )
}

// ── SpritePairGroup: one column in the sprite row ────────────────────────────
// Shows [normal | shiny] with a label underneath
function SpritePairGroup({ config, sprites, palettes }) {
  const spriteNode = findSprite(sprites, config.sprite)
  const normalPalObj = findPalette(palettes, config.normalPal)
  const shinyPalObj = findPalette(palettes, config.shinyPal)

  if (!spriteNode) return null

  const normalColors = normalPalObj?.colors ?? null
  const shinyColors = shinyPalObj?.colors ?? null

  return (
    <div className="pkm-sprite-group">
      <div className="pkm-sprite-pair">
        <div className="pkm-spr-col">
          <NormalSprite spritePath={spriteNode.path} label={config.label} />
          <span className="pkm-spr-sub">normal</span>
        </div>
        <div className="pkm-spr-col">
          {normalColors && shinyColors ? (
            <ShinySprite
              spritePath={spriteNode.path}
              normalColors={normalColors}
              shinyColors={shinyColors}
              label={config.label}
            />
          ) : (
            <div className="pkm-spr-placeholder" title="no shiny palette" />
          )}
          <span className="pkm-spr-sub shiny">shiny</span>
        </div>
      </div>
      <span className="pkm-sprite-label">{config.label}</span>
    </div>
  )
}

// ── Palette row ───────────────────────────────────────────────────────────────
function PaletteRow({ palette, onImport }) {
  const [importState, setImportState] = useState('idle')

  const handleImport = async () => {
    if (importState !== 'idle') return
    setImportState('loading')
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

  const displayName = palette.name.replace(/\.pal$/i, '')

  return (
    <div className="pkm-palette-row">
      <span className="pkm-palette-name">{displayName}</span>
      <div className="pkm-palette-swatches">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
      <div className="pkm-palette-actions">
        <a
          className="pkm-act-btn"
          href={`${API}/palette-library/sprite?path=${encodeURIComponent(palette.path)}`}
          download={palette.name}
          title="Download .pal"
        >
          <Download size={11} />
        </a>
        <button
          className={`pkm-act-btn ${importState === 'done' ? 'done' : importState === 'error' ? 'err' : ''}`}
          onClick={handleImport}
          disabled={importState === 'loading'}
          title="Import to Porypal"
        >
          {importState === 'done' ? (
            <Check size={11} />
          ) : importState === 'error' ? (
            <X size={11} />
          ) : importState === 'loading' ? (
            <Loader size={11} className="pkm-spin" />
          ) : (
            <FolderInput size={11} />
          )}
        </button>
      </div>
    </div>
  )
}

// ── Form section (Base / mega / gmax / etc.) ─────────────────────────────────
function FormSection({ node, label, onImport, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)

  const sprites = node.sprites ?? []
  const palettes = node.palettes ?? []

  if (!sprites.length && !palettes.length) return null

  return (
    <div className="pkm-form-section">
      <button className="pkm-form-header" onClick={() => setOpen(o => !o)}>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <span className="pkm-form-label">{label}</span>
        <span className="pkm-form-count">
          {palettes.length} pal{palettes.length !== 1 ? 's' : ''}
        </span>
      </button>

      {open && (
        <div className="pkm-form-body">
          {sprites.length > 0 && (
            <div className="pkm-sprite-row">
              {SPRITE_CONFIGS.map(cfg => (
                <SpritePairGroup
                  key={cfg.key}
                  config={cfg}
                  sprites={sprites}
                  palettes={palettes}
                />
              ))}
            </div>
          )}

          {palettes.length > 0 && (
            <div className="pkm-palettes">
              {palettes.map(p => (
                <PaletteRow key={p.path} palette={p} onImport={onImport} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main card ─────────────────────────────────────────────────────────────────
export function PokemonCard({ node, onImport }) {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  const handleToggle = async () => {
    if (!open && !data && !loading) {
      setLoading(true)
      setError(false)
      try {
        const res = await fetch(
          `${API}/palette-library/pokemon-node?path=${encodeURIComponent(node.path)}`
        )
        if (!res.ok) throw new Error(res.status)
        setData(await res.json())
      } catch (e) {
        console.error('PokemonCard:', node.path, e)
        setError(true)
      } finally {
        setLoading(false)
      }
    }
    setOpen(o => !o)
  }

  const iconSprite = data?.sprites
    ? findSprite(data.sprites, 'icon.png') ||
      findSprite(data.sprites, 'front.png') ||
      findSprite(data.sprites, 'anim_front.png')
    : null

  const subformEntries = Object.entries(data?.subforms ?? {})

  return (
    <div className={`pkm-card ${open ? 'is-open' : ''}`}>
      <button className="pkm-card-header" onClick={handleToggle}>
        {iconSprite ? (
          <IconSprite spritePath={iconSprite.path} />
        ) : (
          <div className="pkm-spr-placeholder small" />
        )}
        <span className="pkm-card-name">{node.name}</span>
        {loading && <Loader size={11} className="pkm-spin pkm-card-loader" />}
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
      </button>

      {open && (
        <div className="pkm-card-body">
          {loading && (
            <div className="pkm-card-status">
              <Loader size={12} className="pkm-spin" /> loading…
            </div>
          )}
          {error && (
            <div className="pkm-card-status error">
              failed to load — {node.path}
            </div>
          )}
          {data && (
            <>
              <FormSection
                node={data}
                label="Base"
                onImport={onImport}
                defaultOpen
              />
              {subformEntries.map(([formName, formNode]) => (
                <FormSection
                  key={formName}
                  node={formNode}
                  label={formName}
                  onImport={onImport}
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}