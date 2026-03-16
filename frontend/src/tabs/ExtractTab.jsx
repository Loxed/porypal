import { useState } from 'react'
import { DropZone } from '../components/DropZone'
import { useFetch } from '../hooks/useFetch'

const API = '/api'

export function ExtractTab() {
  const [file, setFile] = useState(null)
  const [nColors, setNColors] = useState(16)
  const [result, setResult] = useState(null)
  const { loading, error, run } = useFetch()

  const handleFile = (f) => {
    setFile(f)
    setResult(null)
  }

  const handleExtract = async () => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('n_colors', nColors)
    const data = await run(async () => {
      const res = await fetch(`${API}/extract`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) setResult(data)
  }

  const handleDownloadPal = () => {
    const blob = new Blob([result.pal_content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${result.name}.pal`
    a.click()
  }

  return (
    <div className="tab-content">
      <div className="extract-layout">

        <div className="extract-left">
          <DropZone onFile={handleFile} label="Drop sprite to extract palette" />

          <div className="field">
            <label className="field-label">colors (max 16 for GBA)</label>
            <input
              type="number"
              className="field-input"
              min={2} max={16}
              value={nColors}
              onChange={e => setNColors(Number(e.target.value))}
            />
          </div>

          <button className="btn-primary" disabled={!file || loading} onClick={handleExtract}>
            {loading ? 'extracting…' : 'extract palette'}
          </button>

          {error && <p className="error-msg">{error}</p>}
        </div>

        <div className="extract-right">
          {!result && (
            <div className="empty-state">
              <p>upload a sprite to extract a GBA-compatible palette</p>
            </div>
          )}
          {result && (
            <div className="extract-result">
              <p className="section-label">{result.name} — {result.colors.length} colors</p>
              <div className="palette-large">
                {result.colors.map((hex, i) => (
                  <div key={i} className="swatch-large" style={{ background: hex }}>
                    <span className="swatch-label">{i === 0 ? 'transparent' : hex}</span>
                  </div>
                ))}
              </div>
              <button className="btn-primary" onClick={handleDownloadPal}>
                download .pal file
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}