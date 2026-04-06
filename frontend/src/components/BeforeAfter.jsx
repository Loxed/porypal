/**
 * frontend/src/components/BeforeAfter.jsx
 *
 * Drag-to-reveal before/after image comparison.
 * Both images are drawn on a canvas — left of the handle shows `before`,
 * right shows `after`. Zoom controls included.
 *
 * Props:
 *   before  {string}  URL or base64 data URL for the "before" image
 *   after   {string}  URL or base64 data URL for the "after" image
 *   alt     {string}
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import './BeforeAfter.css'

const ZOOM_LEVELS = [0.25, 0.5, 1, 2, 4, 8]

export function BeforeAfter({ before, after, alt = '' }) {
  const [zoom, setZoom]         = useState(1)
  const [split, setSplit]       = useState(0.5)   // 0..1 fraction of canvas width
  const [dragging, setDragging] = useState(false)

  const canvasRef    = useRef()
  const beforeImgRef = useRef(null)
  const afterImgRef  = useRef(null)
  const loadedRef    = useRef({ before: false, after: false })

  // ── Load both images ────────────────────────────────────────────────────────
  useEffect(() => {
    loadedRef.current = { before: false, after: false }

    const loadImg = (src, ref, key) => {
      const img = new window.Image()
      img.onload = () => {
        ref.current = img
        loadedRef.current[key] = true
        if (loadedRef.current.before && loadedRef.current.after) draw(split)
      }
      img.src = src
    }

    if (before) loadImg(before, beforeImgRef, 'before')
    if (after)  loadImg(after,  afterImgRef,  'after')
  }, [before, after])

  // ── Redraw on split or zoom change ──────────────────────────────────────────
  useEffect(() => {
    if (loadedRef.current.before && loadedRef.current.after) draw(split)
  }, [split, zoom])

  function draw(s) {
    const canvas = canvasRef.current
    const bi     = beforeImgRef.current
    const ai     = afterImgRef.current
    if (!canvas || !bi || !ai) return

    const W = bi.naturalWidth
    const H = bi.naturalHeight
    canvas.width  = W
    canvas.height = H
    const ctx = canvas.getContext('2d')

    // Draw before (full)
    ctx.drawImage(bi, 0, 0)

    // Clip right portion and draw after
    const splitX = Math.round(W * s)
    ctx.save()
    ctx.beginPath()
    ctx.rect(splitX, 0, W - splitX, H)
    ctx.clip()
    ctx.drawImage(ai, 0, 0)
    ctx.restore()

    // Draw divider line
    ctx.save()
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'
    ctx.lineWidth   = Math.max(1, Math.round(1 / zoom))
    ctx.beginPath()
    ctx.moveTo(splitX, 0)
    ctx.lineTo(splitX, H)
    ctx.stroke()
    ctx.restore()
  }

  // ── Drag handling ───────────────────────────────────────────────────────────
  const getSplitFromEvent = useCallback((e) => {
    const canvas = canvasRef.current
    if (!canvas) return split
    const rect = canvas.getBoundingClientRect()
    const x    = (e.clientX ?? e.touches?.[0]?.clientX ?? 0) - rect.left
    return Math.max(0, Math.min(1, x / rect.width))
  }, [split])

  const onMouseDown = (e) => {
    // Only start drag if clicking near the handle
    const s = getSplitFromEvent(e)
    if (Math.abs(s - split) < 0.06) {   // within 6% of handle
      setDragging(true)
      e.preventDefault()
    }
  }

  const onMouseMove = useCallback((e) => {
    if (!dragging) return
    setSplit(getSplitFromEvent(e))
  }, [dragging, getSplitFromEvent])

  const onMouseUp = useCallback(() => setDragging(false), [])

  useEffect(() => {
    if (dragging) {
      window.addEventListener('mousemove', onMouseMove)
      window.addEventListener('mouseup', onMouseUp)
    }
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [dragging, onMouseMove, onMouseUp])

  const changeZoom = (delta) =>
    setZoom(z => {
      const next = ZOOM_LEVELS.indexOf(z) + delta
      return (next < 0 || next >= ZOOM_LEVELS.length) ? z : ZOOM_LEVELS[next]
    })

  // Handle position as % of displayed width
  const handlePct = `${(split * 100).toFixed(1)}%`

  return (
    <div className="ba-wrap">
      <div className="zoom-controls">
        <button className="zoom-btn" onClick={() => changeZoom(1)}>+</button>
        <span className="zoom-label">{zoom}×</span>
        <button className="zoom-btn" onClick={() => changeZoom(-1)}>−</button>
        <button className="zoom-btn" onClick={() => setZoom(1)} title="reset">⟳</button>
        <span className="ba-labels">
          <span className="ba-label-before">before</span>
          <span className="ba-label-after">after</span>
        </span>
      </div>

      <div className="ba-scroll">
        <div
          className="ba-canvas-wrap"
          style={{ width: `${zoom * 100}%`, maxWidth: 'none', position: 'relative' }}
        >
          <canvas
            ref={canvasRef}
            className="pixel-img ba-canvas"
            style={{ display: 'block', width: '100%' }}
            onMouseDown={onMouseDown}
            title={alt}
          />
          {/* Handle overlay */}
          <div
            className={`ba-handle ${dragging ? 'dragging' : ''}`}
            style={{ left: handlePct }}
            onMouseDown={onMouseDown}
          >
            <div className="ba-handle-line" />
            <div className="ba-handle-grip">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}