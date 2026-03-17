import { useState } from 'react'
import './BgColorCell.css'

export function BgColorCell({ color, onChange }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal]         = useState(color)

  const commit = () => {
    if (/^#[0-9a-fA-F]{6}$/.test(val)) onChange(val)
    else setVal(color)
    setEditing(false)
  }

  return (
    <div className="sprite-bg-cell" title="input bg — click to override">
      <div className="sprite-bg-swatch" style={{ background: color }}
        onClick={() => { setVal(color); setEditing(e => !e) }} />
      {editing && (
        <input className="sprite-bg-input" value={val}
          onChange={e => setVal(e.target.value)} onBlur={commit}
          onKeyDown={e => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') { setVal(color); setEditing(false) }
          }}
          maxLength={7} autoFocus spellCheck={false} />
      )}
    </div>
  )
}