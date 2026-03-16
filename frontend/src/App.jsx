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
            <span className="palette-count">{palettes.length} palettes loaded</span>
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