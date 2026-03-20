/**
 * PokemonCard.jsx
 *
 * Sprite rendering rules:
 *   icon.png / icon_gba.png  → scored against pokemon/icon_palettes/pal0-5.pal (no shiny)
 *   front / anim_front / back / overworld → normal/shiny pair from the form's own palettes
 *   footprint.png            → skipped entirely
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { ChevronDown, ChevronRight, Loader, Download, FolderInput, Check, X } from 'lucide-react'
import { PaletteStrip } from '../PaletteStrip'
import { remapToShinyPalette } from '../../utils'
import './PokemonCard.css'
import { AnimFrontThumb } from './AnimFrontThumb.jsx'

const API = '/api'

const SKIP_SPRITES    = new Set(['footprint.png'])
const ICON_SPRITE_NAMES = new Set(['icon.png', 'icon_gba.png'])

// ── Module-level caches ───────────────────────────────────────────────────────
const _rawB64Cache   = new Map()
const _remappedCache = new Map()
const _pixelCache    = new Map()

const _iconPalettesCache   = new Map()  // iconPalettesPath → palette nodes
const _iconPalettesPromises = new Map() // iconPalettesPath → in-flight promise

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
      canvas.width  = img.naturalWidth
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

function scorePalette(imageData, paletteHexColors) {
  const data     = imageData.data
  const colorSet = new Set(paletteHexColors.map(h => h.toLowerCase()))
  let matches = 0, total = 0
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

async function loadIconPalettes(iconPalettesPath) {
  if (_iconPalettesCache.has(iconPalettesPath)) return _iconPalettesCache.get(iconPalettesPath)
  if (_iconPalettesPromises.has(iconPalettesPath)) return _iconPalettesPromises.get(iconPalettesPath)

  const promise = fetch(
    `${API}/palette-library/folder?path=${encodeURIComponent(iconPalettesPath)}`
  )
    .then(r => {
      if (!r.ok) { console.warn('[PokemonCard] icon_palettes fetch failed:', r.status, r.url); return [] }
      return r.json()
    })
    .then(nodes => {
      const pals = (nodes || []).filter(n => n.type === 'palette')
      console.log('[PokemonCard] icon palettes loaded from', iconPalettesPath, ':', pals.length, pals.map(p => p.name))
      _iconPalettesCache.set(iconPalettesPath, pals)
      _iconPalettesPromises.delete(iconPalettesPath)
      return pals
    })
    .catch(e => {
      console.error('[PokemonCard] icon_palettes error:', e)
      _iconPalettesPromises.delete(iconPalettesPath)
      _iconPalettesCache.set(iconPalettesPath, [])
      return []
    })

  _iconPalettesPromises.set(iconPalettesPath, promise)
  return promise
}

async function detectSourcePalette(spritePath, palettes) {
  if (!palettes.length) return null
  const pixels = await getPixels(spritePath)
  let bestPal = null, bestScore = -1
  for (const pal of palettes) {
    const score = scorePalette(pixels, pal.colors)
    if (score > bestScore) { bestScore = score; bestPal = pal }
  }
  return bestPal
}

function sortPalettePairs(palettes) {
  const getGroupKey = name => {
    const n = name.toLowerCase().replace(/\.pal$/, '')
    return n.replace(/(?:^|_)(?:normal|shiny)(?:_|$)/, m => m.replace(/normal|shiny/, '\x00'))
  }
  const getOrder = name => {
    const n = name.toLowerCase()
    if (n.includes('normal')) return 0
    if (n.includes('shiny'))  return 1
    return 2
  }
  return [...palettes].sort((a, b) => {
    const ga = getGroupKey(a.name), gb = getGroupKey(b.name)
    if (ga !== gb) return ga.localeCompare(gb)
    return getOrder(a.name) - getOrder(b.name)
  })
}

function findPalettePair(sourcePal, allPalettes) {
  const srcName  = sourcePal.name.toLowerCase()
  const isNormal = srcName.includes('normal')
  const isShiny  = srcName.includes('shiny')

  if (!isNormal && !isShiny) return { normalPal: sourcePal, shinyPal: sourcePal }

  const partnerName = isNormal
    ? srcName.replace('normal', 'shiny')
    : srcName.replace('shiny',  'normal')

  const partnerPal = allPalettes.find(p => p.name.toLowerCase() === partnerName) ?? sourcePal
  return isNormal
    ? { normalPal: sourcePal, shinyPal: partnerPal }
    : { normalPal: partnerPal, shinyPal: sourcePal }
}

// ── RemappedSprite ─────────────────────────────────────────────────────────────

function RemappedSprite({ spritePath, fromColors, toColors, alt, small = false }) {
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

  const cls = small ? 'pkm-spr small' : 'pkm-spr'

  if (status === 'error')
    return <div className={`pkm-spr-placeholder${small ? ' small' : ''}`} title="remap failed" />
  if (status !== 'done' || !src) {
    return (
      <div className={`pkm-spr-placeholder${small ? ' small' : ''} loading`}>
        {status === 'loading' && <Loader size={small ? 8 : 10} className="pkm-spin" />}
      </div>
    )
  }
  return <img className={cls} src={`data:image/png;base64,${src}`} alt={alt} draggable={false} />
}

// ── DynamicSpritePair (normal / shiny) ────────────────────────────────────────

function DynamicSpritePair({ sprite, palettes }) {
  const [detected, setDetected] = useState(null)
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

  const palLine = detected && detected !== 'error'
    ? detected.normalPal.name === detected.shinyPal.name
      ? detected.normalPal.name.replace(/\.pal$/i, '')
      : `${detected.normalPal.name.replace(/\.pal$/i, '')} / ${detected.shinyPal.name.replace(/\.pal$/i, '')}`
    : null

  return (
    <div className="pkm-sprite-group">
      <div className="pkm-sprite-pair">
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

      <span className="pkm-sprite-label">{label}</span>
      {palLine && <span className="pkm-sprite-pal">{palLine}</span>}
    </div>
  )
}

// ── IconSpriteDisplay ─────────────────────────────────────────────────────────
// Uses a ref for onDetected to avoid stale closure — the effect dep array only
// contains sprite.path, but we always call the latest onDetected via the ref.

function IconSpriteDisplay({ sprite, onDetected, iconPalettesPath }) {
  const [status, setStatus]   = useState('loading')
  const [src, setSrc]         = useState(null)
  const [palName, setPalName] = useState(null)

  // Keep a ref to the latest onDetected so the async effect never goes stale
  const onDetectedRef = useRef(onDetected)
  useEffect(() => { onDetectedRef.current = onDetected })

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    setSrc(null)
    setPalName(null)

    Promise.all([loadIconPalettes(iconPalettesPath), loadSpriteB64(sprite.path)])
      .then(async ([iconPalettes, b64]) => {
        if (cancelled) return

        if (!iconPalettes.length) {
          console.warn('[PokemonCard] no icon palettes found for', sprite.name)
          setSrc(b64)
          setStatus('done')
          return
        }

        const pixels = await getPixels(sprite.path)
        let best = null, bestScore = -1
        for (const pal of iconPalettes) {
          const score = scorePalette(pixels, pal.colors)
          if (score > bestScore) { bestScore = score; best = pal }
        }

        console.log('[PokemonCard]', sprite.name, '→ best icon pal:', best?.name, 'score:', bestScore)

        if (!best || cancelled) return

        const remapped = await remapToShinyPalette(b64, best.colors, best.colors)
        if (cancelled) return

        const name = best.name.replace(/\.pal$/i, '')
        setSrc(remapped)
        setPalName(name)
        onDetectedRef.current?.(sprite.path, best)
        setStatus('done')
      })
      .catch(e => {
        console.error('[PokemonCard] icon detection error for', sprite.name, e)
        if (!cancelled) setStatus('error')
      })

    return () => { cancelled = true }
  }, [sprite.path, iconPalettesPath])

  if (status === 'error') return null

  const spriteName = sprite.name.replace(/\.png$/i, '')

  return (
    <div className="pkm-sprite-group">
      <div className="pkm-spr-col">
        {status !== 'done' || !src ? (
          <div className="pkm-spr-placeholder loading">
            {status === 'loading' && <Loader size={10} className="pkm-spin" />}
          </div>
        ) : (
          <img
            className="pkm-spr"
            src={`data:image/png;base64,${src}`}
            alt={spriteName}
            draggable={false}
          />
        )}
        <span className="pkm-spr-sub">icon</span>
      </div>

      <span className="pkm-sprite-label">{spriteName}</span>
      {/* Show the matched icon palette name clearly below the sprite label */}
      {palName
        ? <span className="pkm-sprite-pal">{palName}</span>
        : <span className="pkm-sprite-pal pkm-sprite-pal--loading">…</span>
      }
    </div>
  )
}

// ── PaletteRow ────────────────────────────────────────────────────────────────

function PaletteRow({ palette, onImport, badge }) {
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
      <span className="pkm-pal-label" title={displayName}>
        {displayName}
      </span>
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

// ── FormSection ───────────────────────────────────────────────────────────────

function FormSection({ node, label, onImport, defaultOpen = false }) {
  const [open, setOpen]           = useState(defaultOpen)
  // spritePath → palette node, populated async by IconSpriteDisplay children
  const [iconPalMap, setIconPalMap] = useState({})

  // Derive icon_palettes path from the node's own path:
  // e.g. "emerald/pokemon/abomasnow" → "emerald/pokemon/icon_palettes"
  const iconPalettesPath = node.path.split('/').slice(0, -1).join('/') + '/icon_palettes'

  const palettes    = sortPalettePairs(node.palettes ?? [])
  const allSprites  = (node.sprites ?? []).filter(s => !SKIP_SPRITES.has(s.name.toLowerCase()))
  const iconSprites = allSprites.filter(s =>  ICON_SPRITE_NAMES.has(s.name.toLowerCase()))
  const mainSprites = allSprites.filter(s => !ICON_SPRITE_NAMES.has(s.name.toLowerCase()))

  // Stable callback — useCallback so the ref inside IconSpriteDisplay always
  // points to a function that has access to the latest setIconPalMap
  const handleIconDetected = useCallback((spritePath, pal) => {
    setIconPalMap(prev => ({ ...prev, [spritePath]: pal }))
  }, [])

  // Deduplicate: if icon.png and icon_gba.png both land on pal2, show one row
  // badged "icon / icon_gba"; if they land on different pals, two separate rows
  const iconPalEntries = Object.values(
    Object.entries(iconPalMap).reduce((acc, [spritePath, pal]) => {
      const spriteName = spritePath.split('/').pop().replace(/\.png$/i, '')
      if (!acc[pal.path]) acc[pal.path] = { pal, sprites: [] }
      acc[pal.path].sprites.push(spriteName)
      return acc
    }, {})
  )

  if (!allSprites.length && !palettes.length) return null

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
          {/* Main sprites: normal / shiny pairs */}
          {(mainSprites.length > 0 || iconSprites.length > 0) && (
            <div className="pkm-sprite-row">
              {mainSprites.length > 0 && palettes.length > 0 && mainSprites.map(sprite => (
                <DynamicSpritePair key={sprite.path} sprite={sprite} palettes={palettes} />
              ))}
              {iconSprites.map(sprite => (
                <IconSpriteDisplay
                  key={sprite.path}
                  sprite={sprite}
                  onDetected={handleIconDetected}
                  iconPalettesPath={iconPalettesPath}
                />
              ))}
            </div>
          )}

          {/* Palette list: regular pals first, then a divider, then icon pals */}
          {(palettes.length > 0 || iconPalEntries.length > 0) && (
            <div className="pkm-palettes">
              {palettes.map(p => (
                <PaletteRow key={p.path} palette={p} onImport={onImport} />
              ))}
              {iconPalEntries.length > 0 && palettes.length > 0 && (
                <div className="pkm-pal-divider" />
              )}
              {iconPalEntries.map(({ pal, sprites }) => (
                <PaletteRow
                  key={pal.path}
                  palette={pal}
                  onImport={onImport}
                  badge={sprites.join(' / ')}
                />
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

  const iconSprite = data?.sprites?.find(s => ICON_SPRITE_NAMES.has(s.name.toLowerCase()))
      ?? data?.sprites?.find(s => ['front.png', 'anim_front.png'].includes(s.name.toLowerCase()))
    const subformEntries = Object.entries(data?.subforms ?? {})

    return (
      <div className={`pkm-card ${open ? 'is-open' : ''}`}>
        <button className="pkm-card-header" onClick={handleToggle}>
          <AnimFrontThumb
            path={`${node.path}/anim_front.png`}
            size={24}
            className="pkm-spr small"
          />
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
                  <FormSection key={formName} node={formNode} label={formName} onImport={onImport} />
                ))}
              </>
            )}
          </div>
        )}
      </div>
    )
  }