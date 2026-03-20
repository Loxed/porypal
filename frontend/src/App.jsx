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
import './App.css'

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
    <Modal title="support the project" onClose={onClose}>
      <p className="modal-desc">
        The best way to support porypal is to star the repo on GitHub. It takes two seconds and helps the project get visibility.
      </p>

      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ height: 120, background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--border2)' }}>screenshot: repo without star</span>
          </div>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ height: 120, background: 'var(--surface2)', border: '1px solid #e3b34144', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: '#e3b34188' }}>screenshot: repo with star</span>
          </div>
        </div>
      </div>

      <a
        href="https://github.com/loxed/porypal"
        target="_blank"
        rel="noopener noreferrer"
        className="btn-primary"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, textDecoration: 'none' }}
        onClick={onClose}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>
        </svg>
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
              <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>
              </svg>
              Support the project :)
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
      </main>
    </div>
  )
}