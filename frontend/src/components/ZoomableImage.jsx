import { useState, useRef, useCallback } from 'react'
import './ZoomableImage.css'

const MIN_ZOOM = 1
const MAX_ZOOM = 16

export function ZoomableImage({ src, alt = '', picking = false, onPick }) {
  const [zoom, setZoom] = useState(1)
  const [hoverColor, setHoverColor] = useState(null)
  const [hoverPos, setHoverPos] = useState(null)
  const canvasRef = useRef()
  const imgRef = useRef()

  // Draw image into hidden canvas for pixel sampling whenever src changes
  const canvasRefCallback = useCallback((canvas) => {
    canvasRef.current = canvas
    if (!canvas || !src) return
    const img = new window.Image()
    img.onload = () => {
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d').drawImage(img, 0, 0)
    }
    img.src = `data:image/png;base64,${src}`
  }, [src])

  const changeZoom = (delta) => {
    setZoom(z => {
      const next = delta > 0 ? z * 2 : z / 2
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next))
    })
  }

  const getColorAtEvent = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return null
    // Use the img element's rect — already accounts for zoom + scroll
    const rect = imgRef.current.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const x = Math.floor((e.clientX - rect.left) * scaleX)
    const y = Math.floor((e.clientY - rect.top) * scaleY)
    if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return null
    const [r, g, b] = canvas.getContext('2d').getImageData(x, y, 1, 1).data
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase()
  }

  const handleMouseMove = (e) => {
    if (!picking) return
    setHoverPos({ x: e.clientX, y: e.clientY })
    setHoverColor(getColorAtEvent(e))
  }

  const handleMouseLeave = () => {
    setHoverPos(null)
    setHoverColor(null)
  }

  const handleClick = (e) => {
    if (!picking || !onPick) return
    e.stopPropagation()
    const hex = getColorAtEvent(e)
    if (hex) onPick(hex)
  }

  return (
    <>
      <div className={`zoomable-wrap ${picking ? 'zoomable-picking' : ''}`}>
        <div className="zoom-controls">
          <button className="zoom-btn" onClick={() => changeZoom(1)}>+</button>
          <span className="zoom-label">{zoom}×</span>
          <button className="zoom-btn" onClick={() => changeZoom(-1)}>−</button>
          <button className="zoom-btn" onClick={() => setZoom(2)} title="reset">⟳</button>
        </div>
        <div className="zoomable-scroll">
          <img
            ref={imgRef}
            src={`data:image/png;base64,${src}`}
            alt={alt}
            className="pixel-img"
            style={{ width: `${zoom * 100}%`, maxWidth: 'none' }}
            draggable={false}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={handleClick}
          />
        </div>
        {/* hidden canvas for pixel sampling */}
        <canvas ref={canvasRefCallback} className="zoomable-sample-canvas" />
      </div>

      {/* floating color preview — rendered in place, position: fixed tracks cursor */}
      {picking && hoverPos && hoverColor && (
        <div className="pipette-preview" style={{ left: hoverPos.x + 16, top: hoverPos.y + 16 }}>
          <div className="pipette-swatch" style={{ background: hoverColor }} />
          <span className="pipette-hex">{hoverColor}</span>
        </div>
      )}
    </>
  )
}