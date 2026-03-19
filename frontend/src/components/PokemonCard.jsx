/**
 * PokemonCard.jsx
 *
 * Fully dynamic — no hardcoded sprite/palette mappings.
 *
 * For each PNG found in the pokemon folder:
 *   1. Load pixel data
 *   2. Score every available .pal by counting exact pixel color matches
 *   3. Best-scoring palette = sourcePal (the one the file is encoded with)
 *   4. Find the normal/shiny partner by string substitution:
 *        *normal* ↔ *shiny*  (handles normal.pal, normal_gba.pal, overworld_normal.pal, …)
 *   5. Render  [sourcePal→normalPal | sourcePal→shinyPal]
 *      When sourcePal === targetPal the remap is identity → raw appearance
 */

import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronRight, Loader, Download, FolderInput, Check, X } from 'lucide-react'
import { PaletteStrip } from './PaletteStrip'
import { remapToShinyPalette } from '../utils'
import './PokemonCard.css'

const API = '/api'

// Sprites to always skip
const SKIP_SPRITES = new Set(['footprint.png'])

// ── Module-level caches ───────────────────────────────────────────────────────
const _rawB64Cache   = new Map()  // spritePath → raw base64
const _remappedCache = new Map()  // `path::from::to` → remapped base64
const _pixelCache    = new Map()  // spritePath → ImageData (for detection)

// ── Helpers ───────────────────────────────────────────────────────────────────

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

async function getPixels(spritePath) {
  if (_pixelCache.has(spritePath)) return _pixelCache.get(spritePath)
  const b64 = await loadSpriteB64(spritePath)
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d').drawImage(img, 0, 0)
      const id = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height)
      _pixelCache.set(spritePath, id)
      resolve(id)
    }
    img.onerror = reject
    img.src = `data:image/png;base64,${b64}`
  })
}

/**
 * Score a palette against image pixels.
 * Returns fraction of opaque pixels whose color exactly matches a palette color.
 */
function scorePalette(imageData, paletteHexColors) {
  const data = imageData.data
  const colorSet = new Set()
  for (const hex of paletteHexColors) {
    colorSet.add(hex.toLowerCase())
  }
  let matches = 0
  let total = 0
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 128) continue
    total++
    const hex = '#' +
      data[i    ].toString(16).padStart(2, '0') +
      data[i + 1].toString(16).padStart(2, '0') +
      data[i + 2].toString(16).padStart(2, '0')
    if (colorSet.has(hex)) matches++
  }
  return total === 0 ? 0 : matches / total
}

/**
 * Detect which palette a sprite is encoded with by finding the best match score.
 */
async function detectSourcePalette(spritePath, palettes) {
  if (!palettes.length) return null
  const pixels = await getPixels(spritePath)
  let bestPal   = null
  let bestScore = -1
  for (const pal of palettes) {
    const score = scorePalette(pixels, pal.colors)
    if (score > bestScore) {
      bestScore = score
      bestPal   = pal
    }
  }
  return bestPal
}

/**
 * Sort palettes so normal/shiny pairs are adjacent.
 * Order: normal.pal, shiny.pal, normal_gba.pal, shiny_gba.pal, overworld_normal.pal, …
 * General rule: group by prefix (everything except the normal/shiny word),
 * within each group normal comes before shiny.
 */
function sortPalettePairs(palettes) {
  const getGroupKey = (name) => {
    const n = name.toLowerCase().replace(/\.pal$/, '')
    // Replace the normal/shiny word (with optional surrounding _ or nothing) with a placeholder
    return n.replace(/(?:^|_)(?:normal|shiny)(?:_|$)/, match => match.replace(/normal|shiny/, '\x00'))
  }
  const getOrder = (name) => {
    const n = name.toLowerCase()
    if (n.includes('normal')) return 0
    if (n.includes('shiny'))  return 1
    return 2
  }
  return [...palettes].sort((a, b) => {
    const ga = getGroupKey(a.name)
    const gb = getGroupKey(b.name)
    if (ga !== gb) return ga.localeCompare(gb)
    return getOrder(a.name) - getOrder(b.name)
  })
}

/**
 * Given a detected source palette, find its normal and shiny counterparts.
 *
 * Pairing rule: substitute 'normal' ↔ 'shiny' in the palette filename.
 *   normal.pal           ↔  shiny.pal
 *   normal_gba.pal       ↔  shiny_gba.pal
 *   overworld_normal.pal ↔  overworld_shiny.pal
 *
 * If no pair exists, both columns show the same (identity remap).
 */
function findPalettePair(sourcePal, allPalettes) {
  const srcName  = sourcePal.name.toLowerCase()
  const isNormal = srcName.includes('normal')
  const isShiny  = srcName.includes('shiny')

  if (!isNormal && !isShiny) {
    // No normal/shiny in name — identity on both sides
    return { normalPal: sourcePal, shinyPal: sourcePal }
  }

  const partnerName = isNormal
    ? srcName.replace('normal', 'shiny')
    : srcName.replace('shiny', 'normal')

  const partnerPal = allPalettes.find(p => p.name.toLowerCase() === partnerName) ?? sourcePal

  return isNormal
    ? { normalPal: sourcePal, shinyPal: partnerPal }
    : { normalPal: partnerPal, shinyPal: sourcePal }
}

// ── RemappedSprite ────────────────────────────────────────────────────────────

function RemappedSprite({ spritePath, fromColors, toColors, alt }) {
  const [status, setStatus] = useState('idle')
  const [src, setSrc]       = useState(null)

  useEffect(() => {
    if (!spritePath || !fromColors?.length || !toColors?.length) return
    const cacheKey = `${spritePath}::${fromColors.join(',')}::${toColors.join(',')}`
    if (_remappedCache.has(cacheKey)) {
      setSrc(_remappedCache.get(cacheKey))
      setStatus('done')
      return
    }
    let cancelled = false
    setStatus('loading')
    loadSpriteB64(spritePath)
      .then(b64 => remapToShinyPalette(b64, fromColors, toColors))
      .then(remapped => {
        if (cancelled) return
        _remappedCache.set(cacheKey, remapped)
        setSrc(remapped)
        setStatus('done')
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [spritePath, fromColors, toColors])

  if (status === 'error') return <div className="pkm-spr-placeholder" title="remap failed" />
  if (status !== 'done' || !src) {
    return (
      <div className="pkm-spr-placeholder loading">
        {status === 'loading' && <Loader size={10} className="pkm-spin" />}
      </div>
    )
  }
  return (
    <img
      className="pkm-spr"
      src={`data:image/png;base64,${src}`}
      alt={alt}
      draggable={false}
    />
  )
}

// ── DynamicSpritePair ─────────────────────────────────────────────────────────
// Detects source palette automatically, then renders [normal | shiny].

function DynamicSpritePair({ sprite, palettes }) {
  const [detected, setDetected] = useState(null) // null=loading | 'error' | { sourcePal, normalPal, shinyPal }
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    setDetected(null)
    detectSourcePalette(sprite.path, palettes)
      .then(sourcePal => {
        if (!mountedRef.current) return
        if (!sourcePal) { setDetected('error'); return }
        const { normalPal, shinyPal } = findPalettePair(sourcePal, palettes)
        setDetected({ sourcePal, normalPal, shinyPal })
      })
      .catch(() => { if (mountedRef.current) setDetected('error') })
    return () => { mountedRef.current = false }
  }, [sprite.path, palettes])

  const label = sprite.name.replace(/\.png$/i, '')

  return (
    <div className="pkm-sprite-group">
      <div className="pkm-sprite-pair">

        {/* Normal column */}
        <div className="pkm-spr-col">
          {!detected ? (
            <div className="pkm-spr-placeholder loading"><Loader size={10} className="pkm-spin" /></div>
          ) : detected === 'error' ? (
            <div className="pkm-spr-placeholder" title="detection failed" />
          ) : (
            <RemappedSprite
              spritePath={sprite.path}
              fromColors={detected.sourcePal.colors}
              toColors={detected.normalPal.colors}
              alt={`${label} normal`}
            />
          )}
          <span className="pkm-spr-sub">normal</span>
        </div>

        {/* Shiny column */}
        <div className="pkm-spr-col">
          {!detected ? (
            <div className="pkm-spr-placeholder loading"><Loader size={10} className="pkm-spin" /></div>
          ) : detected === 'error' ? (
            <div className="pkm-spr-placeholder" title="detection failed" />
          ) : (
            <RemappedSprite
              spritePath={sprite.path}
              fromColors={detected.sourcePal.colors}
              toColors={detected.shinyPal.colors}
              alt={`${label} shiny`}
            />
          )}
          <span className="pkm-spr-sub shiny">shiny</span>
        </div>

      </div>

      {/* Label shows sprite name + detected source palette as tooltip */}
      <span
        className="pkm-sprite-label"
        title={detected && detected !== 'error' ? `source: ${detected.sourcePal.name}` : ''}
      >
        {label}
      </span>
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
    <div className="pkm-pal-row">
      <span className="pkm-pal-label" title={displayName}>{displayName}</span>
      <div className="pkm-pal-strip">
        <PaletteStrip
          colors={palette.colors}
          usedIndices={palette.colors.map((_, i) => i)}
          checkSize="50%"
        />
      </div>
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
        {importState === 'done'     ? <Check size={11} />
        : importState === 'error'   ? <X size={11} />
        : importState === 'loading' ? <Loader size={11} className="pkm-spin" />
        : <FolderInput size={11} />}
      </button>
    </div>
  )
}

// ── Form section (Base / mega / gmax / etc.) ─────────────────────────────────

function FormSection({ node, label, onImport, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)

  const palettes = sortPalettePairs(node.palettes ?? [])
  const sprites  = (node.sprites ?? []).filter(
    s => !SKIP_SPRITES.has(s.name.toLowerCase())
  )

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
          {sprites.length > 0 && palettes.length > 0 && (
            <div className="pkm-sprite-row">
              {sprites.map(sprite => (
                <DynamicSpritePair
                  key={sprite.path}
                  sprite={sprite}
                  palettes={palettes}
                />
              ))}
            </div>
          )}

          {sprites.length > 0 && palettes.length === 0 && (
            <p style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', padding: '4px 0' }}>
              no palettes found for this form
            </p>
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
  const [open, setOpen]       = useState(false)
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(false)

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

  const iconSprite = data?.sprites?.find(s =>
    ['icon.png', 'icon_gba.png', 'front.png', 'anim_front.png'].includes(s.name.toLowerCase())
  )

  const subformEntries = Object.entries(data?.subforms ?? {})

  return (
    <div className={`pkm-card ${open ? 'is-open' : ''}`}>
      <button className="pkm-card-header" onClick={handleToggle}>
        {iconSprite ? (
          <img
            className="pkm-spr small"
            src={`${API}/palette-library/sprite?path=${encodeURIComponent(iconSprite.path)}`}
            alt=""
            draggable={false}
            onError={e => { e.target.style.display = 'none' }}
          />
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
              <FormSection node={data} label="Base" onImport={onImport} defaultOpen />
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