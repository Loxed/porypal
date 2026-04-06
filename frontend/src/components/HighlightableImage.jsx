/**
 * frontend/src/components/HighlightableImage.jsx
 *
 * Zoomable image rendered to canvas with:
 *   - highlightColors: Set<lowercase hex> — non-matching pixels get a dark overlay
 *   - pipette mode: hover shows which palette color is under the cursor
 *
 * Props:
 *   src              {string}           object URL or base64 PNG
 *   alt              {string}
 *   highlightColors  {Set<string>|null} lowercase hex to keep lit; null = all lit
 *   onPipette        {fn|null}          (hex|null) => void  called on hover
 *   pipetteActive    {bool}             show crosshair cursor + call onPipette
 */

import { useState, useRef, useEffect } from 'react'
import './HighlightableImage.css'

const ZOOM_LEVELS  = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64]
const DARKEN_ALPHA = 0.72

export function HighlightableImage({
  src,
  alt = '',
  highlightColors = null,
  onPipette       = null,
  pipetteActive   = false,
}) {
  const [zoom, setZoom]             = useState(1)
  const [pipetteHex, setPipetteHex] = useState(null)
  const [pipettePos, setPipettePos] = useState(null)

  const canvasRef = useRef()
  const pixelsRef = useRef(null)  // cached ImageData of the source
  const srcRef    = useRef(null)  // tracks last loaded src

  // ── Load source, cache pixels, then draw ─────────────────────────────────
  useEffect(() => {
    if (!src || src === srcRef.current) return
    srcRef.current = src

    const img = new window.Image()
    img.onload = () => {
      const off  = document.createElement('canvas')
      off.width  = img.naturalWidth
      off.height = img.naturalHeight
      off.getContext('2d').drawImage(img, 0, 0)
      pixelsRef.current = off.getContext('2d').getImageData(0, 0, off.width, off.height)
      redraw(pixelsRef.current, highlightColors)
    }
    img.src = src
  }, [src])

  // ── Redraw on every highlightColors change ────────────────────────────────
  useEffect(() => {
    if (pixelsRef.current) redraw(pixelsRef.current, highlightColors)
  }, [highlightColors])

  function redraw(imageData, colors) {
    const canvas = canvasRef.current
    if (!canvas) return
    const { width, height, data } = imageData
    canvas.width  = width
    canvas.height = height
    const ctx = canvas.getContext('2d')

    // Step 1: draw the original pixels
    ctx.putImageData(imageData, 0, 0)

    if (!colors || colors.size === 0) return

    // Step 2: build an overlay image where non-matching pixels are black@DARKEN_ALPHA.
    // Matching pixels stay fully transparent so the original shows through.
    // We must use a second canvas + drawImage to composite properly —
    // putImageData REPLACES pixels (no alpha blending), which would make
    // matching pixels disappear instead of staying visible.
    const ov    = document.createElement('canvas')
    ov.width    = width
    ov.height   = height
    const ovCtx = ov.getContext('2d')
    const ovId  = ovCtx.createImageData(width, height)
    const od    = ovId.data

    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] < 128) continue  // transparent source pixel — skip

      const hex = '#' +
        data[i    ].toString(16).padStart(2, '0') +
        data[i + 1].toString(16).padStart(2, '0') +
        data[i + 2].toString(16).padStart(2, '0')

      if (!colors.has(hex)) {
        // od[i..i+2] = 0 (black) already; set alpha
        od[i + 3] = Math.round(DARKEN_ALPHA * 255)
      }
      // matching: od[i+3] stays 0 → fully transparent → source-over keeps original
    }

    ovCtx.putImageData(ovId, 0, 0)
    // drawImage uses source-over blending — composites overlay atop original
    ctx.drawImage(ov, 0, 0)
  }

  // ── Pipette ───────────────────────────────────────────────────────────────
  // Always read from pixelsRef (original image data), not the composited canvas,
  // so the returned hex is always a true source color regardless of overlay state.
  function getHexAt(e) {
    const canvas = canvasRef.current
    if (!canvas || !pixelsRef.current) return null
    const rect   = canvas.getBoundingClientRect()
    const scaleX = canvas.width  / rect.width
    const scaleY = canvas.height / rect.height
    const x = Math.floor((e.clientX - rect.left) * scaleX)
    const y = Math.floor((e.clientY - rect.top)  * scaleY)
    if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return null
    const { data } = pixelsRef.current
    const i = (y * canvas.width + x) * 4
    if (data[i + 3] < 128) return null
    return '#' +
      data[i    ].toString(16).padStart(2, '0') +
      data[i + 1].toString(16).padStart(2, '0') +
      data[i + 2].toString(16).padStart(2, '0')
  }

  function handleMouseMove(e) {
    if (!pipetteActive) return
    const hex = getHexAt(e)
    setPipetteHex(hex)
    setPipettePos({ x: e.clientX, y: e.clientY })
    onPipette?.(hex)
  }

  function handleMouseLeave() {
    setPipetteHex(null)
    setPipettePos(null)
    if (pipetteActive) onPipette?.(null)
  }

  const changeZoom = (delta) =>
    setZoom(z => {
      const next = ZOOM_LEVELS.indexOf(z) + delta
      return (next < 0 || next >= ZOOM_LEVELS.length) ? z : ZOOM_LEVELS[next]
    })

  return (
    <>
      <div className={`highlightable-wrap ${pipetteActive ? 'is-pipette' : ''}`}>
        <div className="zoom-controls">
          <button className="zoom-btn" onClick={() => changeZoom(1)}>+</button>
          <span className="zoom-label">{zoom}×</span>
          <button className="zoom-btn" onClick={() => changeZoom(-1)}>−</button>
          <button className="zoom-btn" onClick={() => setZoom(1)} title="reset">⟳</button>
        </div>
        <div className="zoomable-scroll">
          <canvas
            ref={canvasRef}
            className="pixel-img"
            style={{ width: `${zoom * 100}%`, maxWidth: 'none', display: 'block' }}
            title={alt}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          />
        </div>
      </div>

      {pipetteActive && pipettePos && pipetteHex && (
        <div
          className="pipette-preview"
          style={{ left: pipettePos.x + 16, top: pipettePos.y + 16 }}
        >
          <div className="pipette-swatch" style={{ background: pipetteHex }} />
          <span className="pipette-hex">{pipetteHex.toUpperCase()}</span>
        </div>
      )}
    </>
  )
}