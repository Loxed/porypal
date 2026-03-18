/**
 * frontend/src/components/ExportDropdown.jsx
 *
 * Reusable "export" dropdown with rename input, download .pal, and save to library.
 *
 * Props:
 *   name        {string}   default filename stem (without .pal)
 *   palContent  {string}   JASC-PAL string to download / save
 */

import { useState, useEffect, useRef } from 'react'
import { ChevronDown, Download, Save, Check, X } from 'lucide-react'
import './ExportDropdown.css'

const API = '/api'

export function ExportDropdown({ name, palContent }) {
  const [open, setOpen]           = useState(false)
  const [saveName, setSaveName]   = useState(name ?? '')
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const ref = useRef()

  // Sync name prop changes (e.g. after a new extraction)
  useEffect(() => { setSaveName(name ?? '') }, [name])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleDownload = () => {
    const blob = new Blob([palContent], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${saveName || name}.pal`
    a.click()
    setOpen(false)
  }

  const handleSave = async () => {
    if (saveState === 'saving') return
    setSaveState('saving')
    try {
      const fd = new FormData()
      fd.append('name', saveName || name)
      fd.append('pal_content', palContent)
      const res = await fetch(`${API}/extract/save`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error()
      setSaveState('saved')
      setTimeout(() => { setSaveState('idle'); setOpen(false) }, 1200)
    } catch {
      setSaveState('error')
      setTimeout(() => setSaveState('idle'), 2000)
    }
  }

  return (
    <div className="export-dropdown" ref={ref}>
      <button
        className={`btn-export ${open ? 'open' : ''}`}
        onClick={() => setOpen(o => !o)}
      >
        export <ChevronDown size={10} />
      </button>

      {open && (
        <div className="export-menu">
          <div className="export-rename">
            <label className="export-rename-label">name</label>
            <input
              className="export-rename-input"
              value={saveName}
              onChange={e => setSaveName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              spellCheck={false}
              autoFocus
            />
          </div>

          <div className="export-divider" />

          <button className="export-item" onClick={handleDownload}>
            <Download size={12} /> download .pal
          </button>

          <button
            className={`export-item export-item--save ${saveState}`}
            onClick={handleSave}
            disabled={saveState === 'saving'}
          >
            {saveState === 'saved'
              ? <><Check size={12} /> saved to library</>
              : saveState === 'error'
              ? <><X size={12} /> failed</>
              : <><Save size={12} /> save to library</>
            }
          </button>
        </div>
      )}
    </div>
  )
}