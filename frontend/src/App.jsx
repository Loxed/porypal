import { useState, useEffect } from 'react'
import { Modal } from './components/Modal'
import { ConvertTab }  from './tabs/ConvertTab'
import { ExtractTab }  from './tabs/ExtractTab'
import { BatchTab }    from './tabs/BatchTab'
import { TilesetTab }  from './tabs/TilesetTab'
import { PalettesTab } from './tabs/PalettesTab'
import { ItemsTab }    from './tabs/ItemsTab'
import { ShinyTab }    from './tabs/ShinyTab'
import { HomeTab }     from './tabs/HomeTab'
import { EightBppTab } from './tabs/EightBppTab'
import './App.css'
import { Star } from 'lucide-react'

// Map between URL hash slugs and internal tab keys
const SLUG_TO_TAB = {
  home:            'home',
  extract:         'extract palette',
  apply:           'apply palette',
  shiny:           'shiny',
  tileset:         'tileset',
  pipeline:        'pipeline',
  groups:          'groups',
  palettes:        'palettes',
  '8bpp':          '8bpp',
}

const TAB_TO_SLUG = Object.fromEntries(
  Object.entries(SLUG_TO_TAB).map(([slug, tab]) => [tab, slug])
)

const TABS = [
  'home',
  'extract palette',
  'apply palette',
  'shiny',
  'tileset',
  'pipeline',
  'groups',
  'palettes',
  '8bpp',
]

const TAB_LABELS = {
  'home':            'home',
  'extract palette': 'extract palette',
  'apply palette':   'apply palette',
  'shiny':           'shiny',
  'tileset':         'tileset',
  'pipeline':        'pipeline',
  'groups':          'groups',
  'palettes':        'palettes',
  '8bpp':            '8bpp',
}

function getTabFromHash() {
  const hash = window.location.hash.replace('#/', '').replace('#', '').toLowerCase()
  return SLUG_TO_TAB[hash] ?? 'home'
}

function setHashForTab(tab) {
  const slug = TAB_TO_SLUG[tab] ?? 'home'
  const newHash = `#/${slug}`
  if (window.location.hash !== newHash) {
    window.history.pushState(null, '', newHash)
  }
}

function SupportModal({ onClose }) {
  return (
    <Modal title="support the project" onClose={onClose} size="xxl">
      <p className="modal-desc">
        The best way to support Porypal is to star the repo on GitHub. It takes seconds and helps the project get visibility :)
      </p>

      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <img
            src={"img/support_unstar.png"}
            alt="repo without star"
            style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <img
            src={"img/support_star.png"}
            alt="repo with star"
            style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 'var(--radius)', border: '1px solid #e3b34144' }}
          />
        </div>
      </div>

      <a
        href="https://github.com/loxed/porypal"
        target="_blank"
        rel="noopener noreferrer"
        className="btn-primary"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, textDecoration: 'none', color: 'white' }}
        onClick={onClose}
        onMouseEnter={e => e.currentTarget.style.color = '#ffd573'}
        onMouseLeave={e => e.currentTarget.style.color = 'white'}
      >
        <Star size={16}/>
        star on github
      </a>
    </Modal>
  )
}

export default function App() {
  const [tab, setTab]               = useState(getTabFromHash)
  const [showSupport, setShowSupport] = useState(false)

  // Sync tab → URL
  useEffect(() => {
    setHashForTab(tab)
  }, [tab])

  // Sync URL → tab (back/forward navigation)
  useEffect(() => {
    const onPop = () => setTab(getTabFromHash())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = (newTab) => setTab(newTab)

  return (
    <div className="app">
      {showSupport && <SupportModal onClose={() => setShowSupport(false)} />}
      <header className="header">
        <div className="header-inner">
          <a className="logo" href="#/home" onClick={e => { e.preventDefault(); setTab('home') }}>
            <img src="/porypal.ico" alt="Porypal" className="logo-icon" />
          </a>
          <nav className="nav">
            {TABS.map(t => (
              <button
                key={t}
                className={`nav-tab ${tab === t ? 'active' : ''}`}
                onClick={() => setTab(t)}
              >
                {TAB_LABELS[t]}
              </button>
            ))}
          </nav>
          <div className="header-right">
            <button
              className="star-btn"
              onClick={() => setShowSupport(true)}
            >
              <Star size={16} />
              support the project
            </button>
          </div>
        </div>
      </header>
      <main className="main">
        {tab === 'home'            && <HomeTab     onNavigate={navigate} />}
        {tab === 'extract palette' && <ExtractTab  />}
        {tab === 'apply palette'   && <ConvertTab  />}
        {tab === 'shiny'           && <ShinyTab    />}
        {tab === 'tileset'         && <TilesetTab  />}
        {tab === 'pipeline'        && <BatchTab    />}
        {tab === 'groups'          && <ItemsTab    />}
        {tab === 'palettes'        && <PalettesTab />}
        {tab === '8bpp'            && <EightBppTab />}
      </main>
    </div>
  )
}