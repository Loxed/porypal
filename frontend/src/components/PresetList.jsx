import { useState } from 'react'
import { Trash2, AlertTriangle, Check, Loader } from 'lucide-react'
import './PresetList.css'

export function PresetList({ presets, defaultIds, activePresetId, onLoad, onDelete, currentState }) {
  const [hoveredId, setHoveredId] = useState(null)
  const [loadingId, setLoadingId] = useState(null)

  const isDirty = (preset) => {
    if (!currentState) return false
    return (
      currentState.tileW !== preset.tile_w ||
      currentState.tileH !== preset.tile_h ||
      currentState.cols !== preset.cols ||
      currentState.rows !== preset.rows ||
      currentState.slots.some(s => s !== null)
    )
  }

  const handleApply = async (id) => {
    setLoadingId(id)
    await onLoad(id)
    setLoadingId(null)
    setHoveredId(null)
  }

  return (
    <div className="preset-list">
      {presets.map(p => {
        const isActive = activePresetId === p.id
        const isHovered = hoveredId === p.id
        const isLoading = loadingId === p.id
        const dirty = isDirty(p)

        return (
          <div
            key={p.id}
            className={`preset-row ${isActive ? 'active' : ''}`}
            onMouseEnter={() => setHoveredId(p.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            <div className="preset-info">
              <span className="preset-name">{p.name}</span>
              <span className="preset-meta">{p.cols}×{p.rows} · {p.tile_w}px</span>
            </div>

            <div className="preset-actions">
              {isLoading ? (
                <span className="preset-loading"><Loader size={13} className="spin"/></span>
              ) : isHovered ? (
                <div className="preset-hover-actions">
                  {dirty && (
                    <span className="preset-warn" title="Will reset current layout">
                      <AlertTriangle size={12}/>
                    </span>
                  )}
                  <button className="preset-apply" onClick={() => handleApply(p.id)}>
                    <Check size={12}/> apply
                  </button>
                  {!defaultIds.has(p.id) && (
                    <button className="preset-delete"
                      onClick={e => { e.stopPropagation(); onDelete(p.id) }}>
                      <Trash2 size={11}/>
                    </button>
                  )}
                </div>
              ) : isActive ? (
                <span className="preset-active-dot" title="active"/>
              ) : null}
            </div>
          </div>
        )
      })}
    </div>
  )
}