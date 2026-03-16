import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import './PaletteStrip.css'

export function PaletteStrip({ colors, usedIndices = [], checkSize = '25%' }) {
  const [hover, setHover] = useState(null)
  const [copied, setCopied] = useState(null)
  const usedSet = new Set(usedIndices)

  const handleClick = (e, hex, i) => {
    e.stopPropagation()
    navigator.clipboard.writeText(hex).then(() => {
      setCopied(i)
      setTimeout(() => setCopied(null), 1500)
    })
  }

  return (
    <div className="palette-strip">
      {colors.map((hex, i) => (
        <div
          key={i}
          className={`palette-swatch ${usedSet.has(i) ? 'used' : 'unused'}`}
          style={{ background: hex, '--check-size': checkSize }}
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
          onClick={e => handleClick(e, hex, i)}
        >
          {(hover === i || copied === i) && (
            <div className="swatch-tooltip">
              {hover === i && <span className="swatch-hex">{hex}</span>}
              {copied === i
                ? <Check size={11} className="swatch-icon copied" />
                : <Copy size={11} className="swatch-icon" />
              }
            </div>
          )}
        </div>
      ))}
    </div>
  )
}