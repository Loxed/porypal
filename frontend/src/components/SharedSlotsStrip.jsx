import { useState } from 'react'
import './SharedSlotsStrip.css'

export function SharedSlotsStrip({ sharedSlots, nShared }) {
  const [hoveredIdx, setHoveredIdx] = useState(null)

  if (!sharedSlots || sharedSlots.length === 0) return null

  return (
    <div className="shared-slots-wrap">
      <div className="shared-slots-header">
        <span className="shared-slots-label">shared indices</span>
        <span className="shared-slots-count">
          {nShared + 1} shared (0–{nShared}) · {sharedSlots.length - nShared - 1} local
        </span>
      </div>
      <div className="shared-slots-strip">
        {sharedSlots.map((slot, i) => (
          <div
            key={i}
            className={`shared-slot ${slot.shared ? 'is-shared' : 'is-local'}`}
            style={{ background: slot.hex }}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            {hoveredIdx === i && (
              <div className="shared-slot-tooltip">
                <span className="shared-slot-idx">{i}</span>
                <span className="shared-slot-hex">{slot.hex}</span>
                <span className={`shared-slot-tag ${slot.shared ? 'tag-shared' : 'tag-local'}`}>
                  {slot.shared ? 'shared' : 'local'}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="shared-slots-bar">
        {sharedSlots.map((slot, i) => (
          <div key={i} className={`shared-bar-tick ${slot.shared ? 'tick-shared' : 'tick-local'}`} />
        ))}
      </div>
    </div>
  )
}