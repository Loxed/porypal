/**
 * frontend/src/components/ProjectLoader.jsx
 */

import { useState, useEffect, useRef } from 'react'
import { Loader, Check, Sparkles, Folder, Clock, X } from 'lucide-react'
import { Modal } from '../Modal'
import './ProjectLoader.css'

const API = '/api'
const HISTORY_KEY = 'porypal_recent_projects'
const MAX_HISTORY = 5
const SMART_LABELS = { pokemon: 'pokemon', items: 'items', trainers: 'trainers' }

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') }
  catch { return [] }
}

function saveHistory(path) {
  const prev = loadHistory().filter(p => p !== path)
  localStorage.setItem(HISTORY_KEY, JSON.stringify([path, ...prev].slice(0, MAX_HISTORY)))
}

export function ProjectLoader({ onClose, onLoaded }) {
  const [path, setPath]         = useState('')
  const [projectName, setName]  = useState('')
  const [scanResult, setScan]   = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [error, setError]       = useState(null)
  const [scanning, setScanning] = useState(false)
  const [saving, setSaving]     = useState(false)
  const [history, setHistory]   = useState(loadHistory)
  const [search, setSearch]     = useState('')
  const inputRef = useRef()

  useEffect(() => { inputRef.current?.focus() }, [])

  const doScan = async (scanPath) => {
    const p = (scanPath ?? path).trim()
    if (!p) return
    setScanning(true)
    setError(null)
    setScan(null)
    try {
      const res = await fetch(`${API}/palette-library/projects/scan`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ path: p }),
      })
      if (!res.ok) throw new Error(await res.text() || 'Could not read folder')
      const data = await res.json()
      setScan(data)
      setSearch('')
      setSelected(new Set(data.folders.filter(f => f.smart_type).map(f => f.name)))
      const parts = p.replace(/\\/g, '/').split('/').filter(Boolean)
      const leaf  = parts.at(-1)
      const above = parts.at(-2) ?? ''
      setName(leaf === 'graphics' ? above : leaf)
    } catch (e) {
      setError(e.message)
    } finally {
      setScanning(false)
    }
  }

  const handleLoad = async () => {
    if (!scanResult || !selected.size) return
    setSaving(true)
    setError(null)
    try {
      const folders = scanResult.folders.filter(f => selected.has(f.name))
      const res = await fetch(`${API}/palette-library/projects/load`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ name: projectName || 'project', root: scanResult.root, folders }),
      })
      if (!res.ok) throw new Error(await res.text())
      saveHistory(path.trim())
      setHistory(loadHistory())
      onLoaded?.()
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const toggleFolder = (name) => setSelected(prev => {
    const next = new Set(prev)
    next.has(name) ? next.delete(name) : next.add(name)
    return next
  })

  const removeHistory = (e, p) => {
    e.stopPropagation()
    const next = loadHistory().filter(h => h !== p)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
    setHistory(next)
  }

  const q             = search.trim().toLowerCase()
  const allFolders    = scanResult?.folders ?? []
  const filteredFolders = q
    ? allFolders.filter(f => f.name.toLowerCase().includes(q))
    : allFolders
  const smartFolders = filteredFolders.filter(f =>  f.smart_type)
  const rawFolders   = filteredFolders.filter(f => !f.smart_type)

  return (
    <Modal title="load project" onClose={onClose} size="lg">

      <div className="proj-field">
        <label className="proj-label">project path</label>
        <div className="proj-path-row">
          <input
            ref={inputRef}
            className="field-input"
            placeholder="/home/you/pokeemerald  or  C:\Users\you\pokeemerald"
            value={path}
            onChange={e => { setPath(e.target.value); setError(null); setScan(null) }}
            onKeyDown={e => e.key === 'Enter' && doScan()}
            spellCheck={false}
            disabled={scanning}
          />
          <button
            className="btn-primary-sm"
            onClick={() => doScan()}
            disabled={!path.trim() || scanning}
          >
            {scanning ? <Loader size={12} className="proj-spin" /> : null}
            scan
          </button>
        </div>
        {error && <p className="error-msg">{error}</p>}
      </div>

      {!scanResult && history.length > 0 && (
        <div className="proj-field">
          <label className="proj-label"><Clock size={10} /> recent</label>
          <div className="proj-history">
            {history.map(p => (
              <div key={p} className="proj-history-row" onClick={() => { setPath(p); doScan(p) }}>
                <Folder size={11} className="proj-history-icon" />
                <span className="proj-history-path">{p}</span>
                <button className="proj-history-remove" onClick={e => removeHistory(e, p)}>
                  <X size={10} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {scanResult && (
        <>
          <div className="proj-field">
            <label className="proj-label">project name</label>
            <input
              className="field-input"
              value={projectName}
              onChange={e => setName(e.target.value)}
              spellCheck={false}
            />
          </div>

          <div className="proj-search-row">
            <input
              className="field-input"
              placeholder="filter folders…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              spellCheck={false}
            />
          </div>

          <div className="proj-folders">
            {smartFolders.length > 0 && (
              <div className="proj-folder-group">
                <div className="proj-group-label">
                  <Sparkles size={11} />
                  smart folders
                  <span className="proj-group-hint">recognised by porypal</span>
                </div>
                {smartFolders.map(f => (
                  <label key={f.name} className={`proj-folder-row ${selected.has(f.name) ? 'checked' : ''}`}>
                    <input type="checkbox" className="proj-checkbox"
                      checked={selected.has(f.name)} onChange={() => toggleFolder(f.name)} />
                    <div className="proj-folder-icon smart"><Sparkles size={10} /></div>
                    <span className="proj-folder-name">{f.name}</span>
                    <span className="proj-folder-type">{SMART_LABELS[f.smart_type] ?? f.smart_type}</span>
                  </label>
                ))}
              </div>
            )}

            {rawFolders.length > 0 && (
              <div className="proj-folder-group">
                <div className="proj-group-label"><Folder size={11} /> other folders</div>
                {rawFolders.map(f => (
                  <label key={f.name} className={`proj-folder-row ${selected.has(f.name) ? 'checked' : ''}`}>
                    <input type="checkbox" className="proj-checkbox"
                      checked={selected.has(f.name)} onChange={() => toggleFolder(f.name)} />
                    <div className="proj-folder-icon raw"><Folder size={10} /></div>
                    <span className="proj-folder-name">{f.name}</span>
                    <span className="proj-folder-type">raw</span>
                  </label>
                ))}
              </div>
            )}

            {!smartFolders.length && !rawFolders.length && (
              <p className="proj-empty">No subfolders found.</p>
            )}
          </div>

          <div className="proj-actions">
            <span className="proj-selected-count">
              {selected.size} folder{selected.size !== 1 ? 's' : ''} selected
            </span>
            <button className="btn-primary"
              onClick={handleLoad}
              disabled={!selected.size || saving || !projectName.trim()}>
              {saving ? 'loading…' : 'load project'}
            </button>
          </div>
        </>
      )}
    </Modal>
  )
}