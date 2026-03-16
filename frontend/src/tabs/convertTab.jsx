import { useState, useEffect } from 'react'
import './ConvertTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { WalkAnimation } from '../components/WalkAnimation'
import { ResultCard } from '../components/ResultCard'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob } from '../utils'

const API = '/api'

function GridIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="0" y="0" width="6" height="6" rx="1"/>
      <rect x="8" y="0" width="6" height="6" rx="1"/>
      <rect x="0" y="8" width="6" height="6" rx="1"/>
      <rect x="8" y="8" width="6" height="6" rx="1"/>
    </svg>
  )
}

function ListIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="0" y="1" width="14" height="3" rx="1"/>
      <rect x="0" y="6" width="14" height="3" rx="1"/>
      <rect x="0" y="11" width="14" height="3" rx="1"/>
    </svg>
  )
}

export function ConvertTab() {
  const [file, setFile] = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [isOWSprite, setIsOWSprite] = useState(false)
  const { loading, error, run } = useFetch()

  useEffect(() => {
    if (!originalB64) { setIsOWSprite(false); return }
    const img = new window.Image()
    img.onload = () => setIsOWSprite(img.width / img.height >= 7.5 && img.width / img.height <= 10.5)
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  const convert = async (f) => {
    const fd = new FormData()
    fd.append('file', f)
    const data = await run(async () => {
      const res = await fetch(`${API}/convert`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) {
      setOriginalB64(data.original)
      setResults(data.results)
      setSelected(data.results.findIndex(r => r.best))
    }
  }

  const handleFile = (f) => {
    setFile(f); setResults([]); setSelected(null); setOriginalB64(null)
    convert(f)
  }

  const handleDownload = async (paletteName) => {
    const fd = new FormData()
    fd.append('file', file); fd.append('palette_name', paletteName)
    const res = await fetch(`${API}/convert/download`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_${paletteName.replace('.pal', '')}.png`)
  }

  const handleDownloadAll = async () => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API}/convert/download-all`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_all_palettes.zip`)
  }

  return (
    <div className="tab-content">
      <div className="convert-layout">

        <div className="convert-left">
          <DropZone onFile={handleFile} label="Drop your sprite" />

          {originalB64 && (
            <div className="original-preview">
              <p className="section-label">original</p>
              {/* full-width zoom */}
              <ZoomableImage src={originalB64} alt="original" />
              {/* animation below if applicable */}
              {isOWSprite && <WalkAnimation spriteB64={originalB64} />}
            </div>
          )}

          {results.length > 0 && (
            <button className="btn-secondary" onClick={handleDownloadAll}>
              download all as zip
            </button>
          )}
          <button className="btn-ghost-subtle" disabled={!file || loading} onClick={() => convert(file)}>
            {loading ? 'converting…' : '↺ re-process'}
          </button>
          {error && <p className="error-msg">{error}</p>}
        </div>

        <div className="convert-right">
          {results.length > 0 && (
            <div className="results-toolbar">
              <span className="results-count">{results.length} palettes</span>
              <div className="view-toggle">
                <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')} title="grid view"><GridIcon /></button>
                <button className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')} title="list view"><ListIcon /></button>
              </div>
            </div>
          )}

          {results.length === 0 && !loading && (
            <div className="empty-state"><p>drop a sprite to see all palette conversions</p></div>
          )}
          {loading && (
            <div className="empty-state"><div className="spinner" /><p>processing…</p></div>
          )}

          <div className={viewMode === 'grid' ? 'results-grid' : 'results-list'}>
            {results.map((r, i) => (
              <ResultCard
                key={r.palette_name}
                result={r}
                selected={selected === i}
                onSelect={() => setSelected(i)}
                onDownload={handleDownload}
                listMode={viewMode === 'list'}
              />
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}