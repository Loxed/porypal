/**
 * frontend/src/components/Library/AnimFrontThumb.jsx
 *
 * Shows the top half of an anim_front.png (64×64 from a 64×128 sheet)
 * with the background color removed automatically.
 *
 * Falls back gracefully: no flicker, no broken-image icon.
 */

import { useEffect, useRef, useState } from 'react'

const API = '/api'

/**
 * Sample the 4 corners of ImageData and return the most common opaque color
 * as [r, g, b], or null if all corners are transparent.
 */
function detectBg(data, w, h) {
  const corners = [
    [0,     0    ],
    [w - 1, 0    ],
    [0,     h - 1],
    [w - 1, h - 1],
  ]
  const counts = {}
  for (const [cx, cy] of corners) {
    const i = (cy * w + cx) * 4
    if (data[i + 3] < 128) continue
    const key = `${data[i]},${data[i+1]},${data[i+2]}`
    counts[key] = (counts[key] ?? 0) + 1
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
  if (!entries.length) return null
  return entries[0][0].split(',').map(Number)
}

/**
 * Props:
 *   path      {string}   virtual path to the anim_front.png
 *   size      {number}   CSS display size in px (default 48)
 *   className {string}
 */
export function AnimFrontThumb({ path, size = 48, className = '' }) {
  const canvasRef = useRef()
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!path) return
    let cancelled = false
    setReady(false)
    setFailed(false)

    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      if (cancelled) return
      try {
        const srcW = img.naturalWidth
        const srcH = img.naturalHeight
        // Crop to top half only when the image is taller than wide (1×2 sheet).
        // If already square (e.g. 64×64) skip the crop entirely.
        const needsCrop = srcH > srcW
        const cropW = srcW
        const cropH = needsCrop ? Math.floor(srcH / 2) : srcH

        // Draw into offscreen canvas to read pixels
        const offscreen = document.createElement('canvas')
        offscreen.width  = cropW
        offscreen.height = cropH
        const octx = offscreen.getContext('2d')
        octx.drawImage(img, 0, 0)

        const imageData = octx.getImageData(0, 0, cropW, cropH)
        const data      = imageData.data
        const bg        = detectBg(data, cropW, cropH)

        if (bg) {
          const [br, bg_, bb] = bg
          for (let i = 0; i < data.length; i += 4) {
            if (data[i] === br && data[i+1] === bg_ && data[i+2] === bb) {
              data[i + 3] = 0  // make transparent
            }
          }
          octx.putImageData(imageData, 0, 0)
        }

        // Paint onto the visible canvas
        const canvas = canvasRef.current
        if (!canvas || cancelled) return
        canvas.width  = cropW
        canvas.height = cropH
        const ctx = canvas.getContext('2d')
        ctx.imageSmoothingEnabled = false
        ctx.clearRect(0, 0, cropW, cropH)
        ctx.drawImage(offscreen, 0, 0)
        setReady(true)
      } catch {
        if (!cancelled) setFailed(true)
      }
    }
    img.onerror = () => {
      if (cancelled) return
      // anim_front.png not found — try front.png instead
      if (!img._triedFront) {
        img._triedFront = true
        const frontPath = path.replace(/anim_front\.png$/i, 'front.png')
        img.src = `${API}/palette-library/sprite?path=${encodeURIComponent(frontPath)}`
      } else {
        setFailed(true)
      }
    }
    img.src = `${API}/palette-library/sprite?path=${encodeURIComponent(path)}`

    return () => { cancelled = true }
  }, [path])

  if (failed) return null

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        width:           size,
        height:          size,
        imageRendering:  'pixelated',
        display:         ready ? 'block' : 'none',
        objectFit:       'contain',
      }}
    />
  )
}