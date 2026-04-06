// frontend/src/tabs/HomeTab.jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { Palette, Paintbrush, Star, Grid2x2, Factory, Layers, BookOpen, ArrowRight } from 'lucide-react'
import './HomeTab.css'

// ── Accent colours per tag ────────────────────────────────────────────────────

const TAG_ACCENT = {
  extract:  '#2980EF',
  apply:    '#EF70EF',
  shiny:    '#FAC000',
  tileset:  '#60A1B8',
  pipeline: '#E62829',
  palettes: '#2980EF',
  groups:   '#915121',
}

// ── Column tracking ───────────────────────────────────────────────────────────

const COL_BREAKPOINTS = [
  { maxWidth: 420, cols: 1 },
  { maxWidth: 720, cols: 2 },
]
const DEFAULT_COLS = 3

function useColumns() {
  const getCols = () => {
    const w = window.innerWidth
    for (const bp of COL_BREAKPOINTS) {
      if (w <= bp.maxWidth) return bp.cols
    }
    return DEFAULT_COLS
  }
  const [cols, setCols] = useState(getCols)
  useEffect(() => {
    const h = () => setCols(getCols())
    window.addEventListener('resize', h, { passive: true })
    return () => window.removeEventListener('resize', h)
  }, [])
  return cols
}

function trailingEmpties(count, cols) {
  if (cols <= 1) return 0
  const r = count % cols
  return r === 0 ? 0 : cols - r
}

// ── Scroll-fade ───────────────────────────────────────────────────────────────

function useScrollFade() {
  const ref = useRef(null)
  const [faded, setFaded] = useState(false)
  const check = useCallback(() => {
    const el = ref.current
    if (!el) return
    setFaded(el.scrollHeight - el.scrollTop - el.clientHeight > 4)
  }, [])
  useEffect(() => {
    const el = ref.current
    if (!el) return
    check()
    el.addEventListener('scroll', check, { passive: true })
    const ro = new ResizeObserver(check)
    ro.observe(el)
    return () => { el.removeEventListener('scroll', check); ro.disconnect() }
  }, [check])
  return { ref, faded }
}

// ── Tool data ─────────────────────────────────────────────────────────────────
//
// attacks: [{ name, desc }]  — name renders bold on the attack line,
//                               desc renders below in small type.
// dex:     short flavour line shown in the strip below the art zone.
// modes:   [{ label, desc, inputs, outputs }] — for ability-style cards.

const TOOLS = [
  {
    tab: 'extract palette', tag: 'extract', name: 'Extract Palette', Icon: Palette,
    image: '/img/preview_extract.png',
    dex: 'Create a new palette from a sprite',
    attacks: [
      { name: 'Import',      desc: 'Drop any sprite to begin extraction.' },
      { name: 'Auto-detect', desc: 'Transparent / background color identified automatically.' },
      { name: 'Reduce',      desc: 'Output is quantised to 16 colors, ready for ROM insertion.' },
    ],
    inputs: ['sprite.png'], outputs: ['sprite.pal'],
  },
  {
    tab: 'apply palette', tag: 'apply', name: 'Apply Palette', Icon: Paintbrush,
    image: '/img/preview_apply.gif',
    dex: 'Apply every palette to a sprite',
    attacks: [
      { name: 'Preview All', desc: 'Sprite is remapped to every library palette at once.' },
      { name: 'Auto-match',  desc: 'Best-matching palettes are highlighted and sorted.' },
      { name: 'Export',      desc: 'Download the converted sprite ready for use.' },
    ],
    inputs: ['sprite.png', 'palette.pal'], outputs: ['sprite.png'],
  },
  {
    tab: 'shiny', tag: 'shiny', name: 'Shiny Manager', Icon: Star,
    image: '/img/preview_shiny.png',
    dex: 'Manage shiny variants of Pokémon',
    modes: [
      {
        label: 'Create a Shiny Palette',
        desc: 'Import a pokémon sprite and a shiny pokémon sprite to get two index-aligned palettes.',
        inputs: ['sprite.png', 'shiny_sprite.png'], outputs: ['normal.pal', 'shiny.pal'],
      },
      {
        label: 'Create a Shiny Sprite',
        desc: 'Import a pokémon sprite, its normal palette, and its shiny palette to create a shiny sprite.',
        inputs: ['sprite.png', 'normal.pal', 'shiny.pal'], outputs: ['shiny_sprite.png'],
      },
    ],
    inputs: null, outputs: null,
  },
  {
    tab: 'tileset', tag: 'tileset', name: 'Tileset Manager', Icon: Grid2x2,
    image: '/img/preview_tileset.png',
    dex: 'Slice and arrange spritesheets',
    attacks: [
      { name: 'Slice',   desc: 'Cuts a spritesheet into individual tiles.' },
      { name: 'Arrange', desc: 'Drag tiles into any layout and save it as a reusable preset.' },
    ],
    inputs: ['spritesheet_4x4.png'], outputs: ['spritesheet_9x1.png'],
  },
  {
    tab: 'pipeline', tag: 'pipeline', name: 'Pipeline', Icon: Factory,
    image: '/img/preview_pipeline.png',
    dex: 'Apply multiple operations on folders',
    attacks: [
      { name: 'Assemble',     desc: 'Create a pipeline by combining multiple steps (extract, apply, etc.).' },
      { name: 'Execute', desc: 'Process a whole folder using the defined pipeline.' },
    ],
    inputs: ['folder/'], outputs: ['palettes/', 'sprites/'],
  },
  {
    tab: 'palettes', tag: 'palettes', name: 'Palette Manager', Icon: Palette,
    image: '/img/preview_palettes.png',
    dex: 'Manage your palettes in one location',
    attacks: [
      { name: 'Load Decomp Project',  desc: 'Import your own decomp project into the library.' },
      { name: 'Preview Assets',  desc: 'Preview your sprites and palettes.' },
      { name: 'Modify', desc: 'Edit, organise, and rearrange existing palettes.' },
    ],
    inputs: ['decomp project', 'palette.pal'], outputs: ['library'],
  },
  {
    tab: 'groups', tag: 'groups', name: 'Group Operations', Icon: Layers,
    image: '/img/preview_groups.png',
    dex: 'Compare and group sprites by shared colours',
    modes: [
      {
        label: 'Variants',
        desc: 'For sprites sharing the same pixel art but different palettes, import all versions and define one as the reference.',
        inputs: ['potion.png', 'super_potion.png'], outputs: ['potion.pal', 'super_potion.pal'],
      },
      {
        label: 'Group Extract',
        desc: 'Import multiple sprites and automatically group them by silhouette. Colors appearing across most sprites are locked to the same index.',
        inputs: ['sprites/'], outputs: ['aligned .pal files'],
      },
    ],
    inputs: null, outputs: null,
  },
]

const QUICKSTART = [
  { title: 'Extract your first palette', desc: 'Extract Palette → drop a sprite → Extract. Download the Oklab result.',                tab: 'extract palette' },
  { title: 'Load a decomp project',      desc: 'Palettes → Browse Library → Load Project… → paste the path to your graphics/ folder.', tab: 'palettes'        },
  { title: 'Remap to every palette',     desc: 'Apply Palette → drop a sprite. Every loaded palette is tested instantly.',              tab: 'apply palette'   },
  { title: 'Batch-process a folder',     desc: 'Pipeline → drop a folder → add Extract + Apply steps → Run.',                          tab: 'pipeline'        },
]

// ── Sub-components ────────────────────────────────────────────────────────────

// Inline IO pills used inside ability blocks (small variant)
function IoRowSmall({ inputs, outputs }) {
  return (
    <div className="home-io home-io--small">
      {inputs.map((v, i) => <span key={i} className="home-io-item">{v}</span>)}
      <ArrowRight size={7} className="home-io-arrow" />
      {outputs.map((v, i) => <span key={i} className="home-io-item home-io-item--out">{v}</span>)}
    </div>
  )
}

// ── Tool card ─────────────────────────────────────────────────────────────────

function ToolCard({ tool, onNavigate }) {
  const { tab, tag, name, Icon, dex, attacks, modes, inputs, outputs } = tool
  const accent = TAG_ACCENT[tag] ?? '#888'
  const { ref: bodyRef, faded } = useScrollFade()

  return (
    <div
      className="home-card"
      style={{ '--card-accent': accent }}
      onClick={() => onNavigate(tab)}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onNavigate(tab)}
    >
      {/* ── Band: [tag] [name] · · · [Icon] ── */}
      <div className="home-card-band">
        <span className="home-card-tag">{tag}</span>
        <span className="home-card-name">{name}</span>
        <div className="home-card-type-icon">
          <Icon size={13} strokeWidth={2} />
        </div>
      </div>

      {/* ── Art zone ── */}
      <div className="home-card-art">
        {tool.image
          ? <img src={tool.image} alt={name} className="home-card-art-img" />
          : <Icon size={28} strokeWidth={1} className="home-card-art-icon" />
        }
      </div>

      {/* ── Dex strip ── */}
      {dex && <div className="home-card-dex">{dex}</div>}

      {/* ── Scrollable body ── */}
      <div className="home-card-body-wrap">
        <div className="home-card-body" ref={bodyRef}>

          {/* Attack-style bullets */}
          {attacks && (
            <div className="home-card-attacks">
              {attacks.map((a, i) => (
                <div key={i} className="home-card-attack">
                  <div className="home-card-attack-energy" />
                  <div className="home-card-attack-content">
                    <span className="home-card-attack-name">{a.name}</span>
                    <span className="home-card-attack-desc">{a.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Ability-style mode blocks */}
          {modes && (
            <div className="home-card-modes">
              {modes.map((m, i) => (
                <div key={i} className="home-card-mode">
                  <div className="home-card-mode-label">
                    <span className="home-card-mode-badge">Ability</span>
                    <span className="home-card-mode-name">{m.label}</span>
                  </div>
                  <p className="home-card-mode-desc">{m.desc}</p>
                  <IoRowSmall inputs={m.inputs} outputs={m.outputs} />
                </div>
              ))}
            </div>
          )}

        </div>
        <div className={`home-card-scroll-fade${faded ? ' is-visible' : ''}`} />
      </div>

      {/* ── Footer bar: inputs → outputs (weakness/retreat style) ── */}
      {inputs && (
        <div className="home-card-footer">
          <div className="home-card-footer-io">
            {inputs.map((v, i) => <span key={i} className="home-io-item">{v}</span>)}
            <ArrowRight size={9} className="home-io-arrow" />
            {outputs.map((v, i) => <span key={i} className="home-io-item home-io-item--out">{v}</span>)}
          </div>
          <ArrowRight size={12} className="home-card-arrow" />
        </div>
      )}
    </div>
  )
}

function EmptyCard() {
  return <div className="home-card home-card--empty" aria-hidden="true" />
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function HomeTab({ onNavigate }) {
  const cols = useColumns()
  const emptyCount = trailingEmpties(TOOLS.length, cols)

  return (
    <div className="tab-content">
      <div className="home-layout">

        <div className="home-hero">
          <p className="home-hero-eyebrow">v3.1 · Gen 3 ROM hacking</p>
          <div className="home-hero-title-row">
            <img src="/porypal.ico" alt="" className="home-hero-icon" />
            <h1 className="home-hero-title">Porypal</h1>
          </div>
          <p className="home-hero-sub">
            Sprite toolchain for Pokémon Gen 3 ROM hacking (pokefirered, pokeruby, pokeemerald, pokeemerald-expansion).
          </p>
        </div>

        <div className="home-section">
          <h2 className="home-section-heading">Tools</h2>
          <div className="home-grid">
            {TOOLS.map(t => <ToolCard key={t.tab} tool={t} onNavigate={onNavigate} />)}
            {Array.from({ length: emptyCount }, (_, i) => <EmptyCard key={`empty-${i}`} />)}
          </div>
        </div>

        {/* <div className="home-section">
          <h2 className="home-section-heading">Getting Started</h2>
          <div className="home-quickstart">
            {QUICKSTART.map((q, i) => (
              <button key={i} className="home-qs-item" onClick={() => onNavigate(q.tab)}>
                <span className="home-qs-num">0{i + 1}</span>
                <span className="home-qs-body">
                  <span className="home-qs-title">{q.title}</span>
                  <span className="home-qs-desc">{q.desc}</span>
                </span>
                <ArrowRight size={13} className="home-qs-arrow" />
              </button>
            ))}
          </div>
        </div> */}

        <div className="home-footer">
          <span className="home-footer-left">porypal v3.1 · by prison_lox</span>
          <div className="home-footer-links">
            <a className="home-footer-link" href="https://github.com/loxed/porypal" target="_blank" rel="noopener noreferrer">github</a>
          </div>
        </div>

      </div>
    </div>
  )
}