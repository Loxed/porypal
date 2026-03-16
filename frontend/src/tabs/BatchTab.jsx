import { useState, useRef } from 'react'
import { useFetch } from '../hooks/useFetch'
import './BatchTab.css'
import { downloadBlob } from '../utils'

const API = '/api'

export function BatchTab({ palettes }) {
  const [files, setFiles] = useState([])
  const [paletteName, setPaletteName] = useState('')
  const { loading, error, run } = useFetch()
  const inputRef = useRef()

  const handleBatch = async () => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    fd.append('palette_name', paletteName)
    await run(async () => {
      const res = await fetch(`${API}/batch`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      downloadBlob(await res.blob(), 'batch_output.zip')
    })
  }

  return (
    <div className="tab-content">
      <div className="batch-layout">

        <div className="field">
          <label className="field-label">sprites</label>
          <button className="btn-secondary" onClick={() => inputRef.current.click()}>
            select files ({files.length} selected)
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*"
            style={{ display: 'none' }}
            onChange={e => setFiles(Array.from(e.target.files))}
          />
        </div>

        {files.length > 0 && (
          <div className="file-list">
            {files.map(f => (
              <span key={f.name} className="file-chip">{f.name}</span>
            ))}
          </div>
        )}

        <div className="field">
          <label className="field-label">target palette</label>
          <select
            className="field-input"
            value={paletteName}
            onChange={e => setPaletteName(e.target.value)}
          >
            <option value="">select palette…</option>
            {palettes.map(p => (
              <option key={p.name} value={p.name}>{p.name.replace('.pal', '')}</option>
            ))}
          </select>
        </div>

        <button
          className="btn-primary"
          disabled={files.length === 0 || !paletteName || loading}
          onClick={handleBatch}
        >
          {loading ? 'processing…' : `convert ${files.length} sprites → zip`}
        </button>

        {error && <p className="error-msg">{error}</p>}

      </div>
    </div>
  )
}
