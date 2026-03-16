import { useState, useEffect } from 'react'
import { ConvertTab } from './tabs/ConvertTab'
import { ExtractTab } from './tabs/ExtractTab'
import { BatchTab } from './tabs/BatchTab'
import { TilesetTab } from './tabs/TilesetTab'
import './App.css'

const API = '/api'
const TABS = ['convert', 'extract', 'batch', 'tileset']

export default function App() {
  const [tab, setTab] = useState('convert')
  const [palettes, setPalettes] = useState([])

  useEffect(() => {
    fetch(`${API}/palettes`)
      .then(r => r.json())
      .then(setPalettes)
      .catch(() => {})
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <a className="logo" href='#' onClick={() => setTab('convert')}>
            <img src="/porypal.ico" alt="Porypal" className="logo-icon" />
          </a>
          <nav className="nav">
            {TABS.map(t => (
              <button
                key={t}
                className={`nav-tab ${tab === t ? 'active' : ''}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </nav>
          <div className="header-right">
            <a
              className="star-btn"
              href="https://github.com/loxed/porypal"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>
              </svg>
              Support the project
            </a>
          </div>
        </div>
      </header>
      <main className="main">
        {tab === 'convert' && <ConvertTab />}
        {tab === 'extract' && <ExtractTab />}
        {tab === 'batch'   && <BatchTab palettes={palettes} />}
        {tab === 'tileset' && <TilesetTab />}
      </main>
    </div>
  )
}