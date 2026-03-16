import { useState } from 'react'
import './ZoomableImage.css'

const MIN_ZOOM = 1
const MAX_ZOOM = 16

export function ZoomableImage({ src, alt = '' }) {
  const [zoom, setZoom] = useState(1)

  const changeZoom = (delta) => {
    setZoom(z => {
      const next = delta > 0 ? z * 2 : z / 2
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next))
    })
  }

  return (
    <div className="zoomable-wrap">
      <div className="zoom-controls">
        <button className="zoom-btn" onClick={() => changeZoom(1)}>+</button>
        <span className="zoom-label">{zoom}×</span>
        <button className="zoom-btn" onClick={() => changeZoom(-1)}>−</button>
        <button className="zoom-btn" onClick={() => setZoom(2)} title="reset">⟳</button>
      </div>
      <div className="zoomable-scroll">
        <img
          src={`data:image/png;base64,${src}`}
          alt={alt}
          className="pixel-img"
          style={{ width: `${zoom * 100}%`, maxWidth: 'none' }}
          draggable={false}
        />
      </div>
    </div>
  )
}
