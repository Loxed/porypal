/**
 * Split a base64-encoded spritesheet into N equal horizontal frames.
 * Returns an array of base64 PNG strings.
 */
export function splitFrames(b64, frameCount) {
  return new Promise((resolve) => {
    const img = new window.Image()
    img.onload = () => {
      const fw = Math.floor(img.width / frameCount)
      const fh = img.height
      const frames = []
      for (let i = 0; i < frameCount; i++) {
        const canvas = document.createElement('canvas')
        canvas.width = fw
        canvas.height = fh
        const ctx = canvas.getContext('2d')
        ctx.imageSmoothingEnabled = false
        ctx.drawImage(img, i * fw, 0, fw, fh, 0, 0, fw, fh)
        frames.push(canvas.toDataURL('image/png').split(',')[1])
      }
      resolve(frames)
    }
    img.src = `data:image/png;base64,${b64}`
  })
}

/**
 * Trigger a file download in the browser.
 */
export function downloadBlob(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
}

// Add these to your existing utils.js

export function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)]
}

// Direct palette swap — no nearest neighbor, just replace palette colors
// Used when palette indices are already correct (mode 1)
export function applyPalette(imageB64, paletteHexColors) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data
      const palette = paletteHexColors.map(hexToRgb)
      const [tr, tg, tb] = palette[0]

      // Build a lookup: original RGB → palette index (from normal palette)
      // Then replace with shiny palette color at same index
      // Since we don't have the index map here, we do nearest-match to normal pal
      // to find the index, then apply shiny color at that index
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) {
          data[i] = tr; data[i+1] = tg; data[i+2] = tb; data[i+3] = 255
          continue
        }
        const r = data[i], g = data[i+1], b = data[i+2]
        // exact match to transparent → slot 0
        if (r === tr && g === tg && b === tb) continue
        let bestIdx = 1, bestDist = Infinity
        for (let j = 1; j < palette.length; j++) {
          const [pr,pg,pb] = palette[j]
          const dist = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
          if (dist < bestDist) { bestDist = dist; bestIdx = j }
        }
        ;[data[i], data[i+1], data[i+2]] = palette[bestIdx]
      }
      ctx.putImageData(imageData, 0, 0)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

// Remap using normal palette to find indices, then render with shiny palette
// normalPalette and shinyPalette are both hex color arrays, same length, same indices
export function remapToShinyPalette(imageB64, normalPaletteHex, shinyPaletteHex) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data
      const normalPal = normalPaletteHex.map(hexToRgb)
      const shinyPal  = shinyPaletteHex.map(hexToRgb)
      const [tr, tg, tb] = normalPal[0]
      const [sr, sg, sb] = shinyPal[0]

      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) {
          data[i] = sr; data[i+1] = sg; data[i+2] = sb; data[i+3] = 255
          continue
        }
        const r = data[i], g = data[i+1], b = data[i+2]
        // bg color → shiny transparent
        if (r === tr && g === tg && b === tb) {
          data[i] = sr; data[i+1] = sg; data[i+2] = sb
          continue
        }
        // find index in normal palette (skip slot 0)
        let bestIdx = 1, bestDist = Infinity
        for (let j = 1; j < normalPal.length; j++) {
          const [pr,pg,pb] = normalPal[j]
          const dist = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
          if (dist < bestDist) { bestDist = dist; bestIdx = j }
        }
        // apply shiny color at same index
        if (bestIdx < shinyPal.length) {
          ;[data[i], data[i+1], data[i+2]] = shinyPal[bestIdx]
        }
      }
      ctx.putImageData(imageData, 0, 0)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

export function detectBgColor(imageB64) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const w = canvas.width - 1
      const h = canvas.height - 1
      const corners = [
        ctx.getImageData(0, 0, 1, 1).data,
        ctx.getImageData(w, 0, 1, 1).data,
        ctx.getImageData(0, h, 1, 1).data,
        ctx.getImageData(w, h, 1, 1).data,
      ].map(d => {
        if (d[3] < 128) return null
        return `#${d[0].toString(16).padStart(2,'0')}${d[1].toString(16).padStart(2,'0')}${d[2].toString(16).padStart(2,'0')}`
      })
      const counts = {}
      for (const c of corners) { if (c) counts[c] = (counts[c] || 0) + 1 }
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])
      resolve(sorted.length > 0 ? sorted[0][0] : '#73C5A4')
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}