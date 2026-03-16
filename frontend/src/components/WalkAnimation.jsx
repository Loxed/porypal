import { useEffect, useRef, useState } from 'react'
import './WalkAnimation.css'
import { splitFrames } from '../utils'

// 0: down
// 1: up
// 2: left (right is just flipped left)
// 3: down step 1
// 4: down step 2
// 5: up step 1
// 6: up step 2
// 7: left step 1
// 8: left step 2

// 3,0,4,0,3,0,4,0 - walk down
// 7,2,8,2,7,2,8,2 - walk left
// 5,1,6,1,5,1,6,1 - walk up
// 7f,2f,8f,2f,7f,2f,8f,2f - walk right (flip left frames)

const SEQUENCE = [
    { f: 3 }, { f: 0 }, { f: 4 }, { f: 0 }, // walk down
    { f: 3 }, { f: 0 }, { f: 4 }, { f: 0 }, // walk down
    // { f: 0 }, { f: 0 }, { f: 0 }, { f: 0 }, // idle down
    { f: 7}, { f: 2 }, { f: 8 }, { f: 2 }, // walk left
    { f: 7}, { f: 2 }, { f: 8 }, { f: 2 }, // walk left
    // { f: 2}, { f: 2 }, { f: 2 }, { f: 2 }, // idle left
    { f: 5 }, { f: 1 }, { f: 6 }, { f: 1 }, // walk up
    { f: 5 }, { f: 1 }, { f: 6 }, { f: 1 }, // walk up
    // { f: 1 }, { f: 1 }, { f: 1 }, { f: 1 }, // idle up
    { f: 7, flip: true}, { f: 2, flip: true}, { f: 8, flip: true}, { f: 2, flip: true}, // walk right
    { f: 7, flip: true}, { f: 2, flip: true}, { f: 8, flip: true}, { f: 2, flip: true}, // walk right
    // { f: 2, flip: true}, { f: 2, flip: true}, { f: 2, flip: true}, { f: 2, flip: true}, // idle right
]
const FRAME_MS = 150
const DISPLAY_SIZE = 120 // fixed square display in CSS px

export function WalkAnimation({ spriteB64 }) {
  const canvasRef = useRef()
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    let timer = null
    setStatus('loading')

    const run = async () => {
      try {
        const b64Frames = await splitFrames(spriteB64, 9)
        if (cancelled) return
        if (b64Frames.length < 9) { setStatus('error'); return }

        // Draw each frame into an offscreen canvas — avoids XrayWrapper issues
        const offscreens = await Promise.all(b64Frames.map(b64 => new Promise((resolve, reject) => {
          const img = new Image()
          img.onload = () => {
            const c = document.createElement('canvas')
            c.width = img.width
            c.height = img.height
            c.getContext('2d').drawImage(img, 0, 0)
            resolve(c)
          }
          img.onerror = reject
          img.src = `data:image/png;base64,${b64}`
        })))

        if (cancelled) return

        const canvas = canvasRef.current
        if (!canvas) return

        const fw = offscreens[0].width
        const fh = offscreens[0].height

        // Canvas internal resolution = one frame (square)
        canvas.width = fw
        canvas.height = fh
        // CSS display size = fixed square
        canvas.style.width = `${DISPLAY_SIZE}px`
        canvas.style.height = `${DISPLAY_SIZE}px`

        const ctx = canvas.getContext('2d')
        ctx.imageSmoothingEnabled = false

        let seq = 0
        const draw = () => {
          const step = SEQUENCE[seq % SEQUENCE.length]
          const src = offscreens[step.f]
          ctx.clearRect(0, 0, fw, fh)
          if (step.flip) {
            ctx.save(); ctx.translate(fw, 0); ctx.scale(-1, 1)
          }
          ctx.drawImage(src, 0, 0)
          if (step.flip) ctx.restore()
          seq++
        }

        draw()
        setStatus('ready')
        timer = setInterval(draw, FRAME_MS)
      } catch {
        if (!cancelled) setStatus('error')
      }
    }

    run()
    return () => { cancelled = true; clearInterval(timer) }
  }, [spriteB64])

  if (status === 'error') return null

  return (
    <div className="walk-animation">
      {status === 'loading' && <div className="walk-loading"><div className="spinner" style={{ width: 16, height: 16 }} /></div>}
      <canvas ref={canvasRef} className="walk-canvas" style={{ display: status === 'ready' ? 'block' : 'none' }} />
    </div>
  )
}