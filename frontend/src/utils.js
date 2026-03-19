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

export function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)]
}

// Direct palette swap — no nearest neighbor, just replace palette colors
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
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) {
          data[i] = tr; data[i+1] = tg; data[i+2] = tb; data[i+3] = 255
          continue
        }
        const r = data[i], g = data[i+1], b = data[i+2]
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

/**
 * Sample the 4 corners of an ImageData pixel array and return the most common
 * opaque color as [r, g, b]. Falls back to `fallback` if all corners are transparent.
 */
function _detectActualBg(data, w, h, fallback) {
  const corners = [
    [0, 0],
    [w - 1, 0],
    [0, h - 1],
    [w - 1, h - 1],
  ]
  const counts = {}
  for (const [cx, cy] of corners) {
    const i = (cy * w + cx) * 4
    if (data[i + 3] < 128) continue
    const key = `${data[i]},${data[i+1]},${data[i+2]}`
    counts[key] = (counts[key] || 0) + 1
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
  if (!entries.length) return fallback
  return entries[0][0].split(',').map(Number)
}

/**
 * Remap using normal palette to find slot indices, then render with shiny palette.
 *
 * Key fix vs old version: instead of assuming normalPal[0] is the bg color
 * actually present in the image (which breaks for icon.png that uses magenta),
 * we sample the image corners to detect the real bg, then treat that as slot 0.
 */
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
      const w = canvas.width
      const h = canvas.height

      const normalPal = normalPaletteHex.map(hexToRgb)
      const shinyPal  = shinyPaletteHex.map(hexToRgb)
      const [sr, sg, sb] = shinyPal[0]

      // Detect the actual transparent/bg color from the image corners.
      // This handles icons (magenta bg) and sprites that use #73C5A4 equally,
      // without assuming normalPal[0] matches what's actually in the file.
      const [tr, tg, tb] = _detectActualBg(data, w, h, normalPal[0])

      for (let i = 0; i < data.length; i += 4) {
        // Alpha-transparent pixel → output shiny bg
        if (data[i + 3] < 128) {
          data[i] = sr; data[i+1] = sg; data[i+2] = sb; data[i+3] = 255
          continue
        }
        const r = data[i], g = data[i+1], b = data[i+2]

        // Actual bg color → output shiny bg
        if (r === tr && g === tg && b === tb) {
          data[i] = sr; data[i+1] = sg; data[i+2] = sb
          continue
        }

        // Find nearest slot in normal palette (skip slot 0 = bg)
        let bestIdx = 1, bestDist = Infinity
        for (let j = 1; j < normalPal.length; j++) {
          const [pr, pg, pb] = normalPal[j]
          const dist = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
          if (dist < bestDist) { bestDist = dist; bestIdx = j }
        }

        // Apply shiny color at same slot index
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


/**
 * Compare two base64 PNG images pixel by pixel in Oklab space.
 */
export function compareVariantPixels(refB64, variantB64, bgHex = '#73c5a4') {
  const hexToRgbLocal = (hex) => {
    const h = hex.replace('#', '')
    return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)]
  }
  const toLinear = (c) => {
    const v = c / 255
    return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
  }
  const toOklab = (r, g, b) => {
    const lr = toLinear(r), lg = toLinear(g), lb = toLinear(b)
    const l = Math.cbrt(0.4122214708*lr + 0.5363325363*lg + 0.0514459929*lb)
    const m = Math.cbrt(0.2119034982*lr + 0.6806995451*lg + 0.1073969566*lb)
    const s = Math.cbrt(0.0883024619*lr + 0.2817188376*lg + 0.6299787005*lb)
    return [
      0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
      1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
      0.0259040371*l + 0.7827717662*m - 0.8086757660*s,
    ]
  }
  const oklabDist = (a, b) =>
    Math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)
  const MISMATCH_THRESHOLD = 0.08
  const loadPixels = (b64) => new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width  = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d').drawImage(img, 0, 0)
      resolve(canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height))
    }
    img.src = `data:image/png;base64,${b64}`
  })
  return Promise.all([loadPixels(refB64), loadPixels(variantB64)]).then(([refData, varData]) => {
    const [bgR, bgG, bgB] = hexToRgbLocal(bgHex)
    const rd = refData.data
    const vd = varData.data
    const len = Math.min(rd.length, vd.length)
    let totalPixels = 0, mismatchedPixels = 0
    for (let i = 0; i < len; i += 4) {
      if (rd[i+3] < 128) continue
      const rR = rd[i], rG = rd[i+1], rB = rd[i+2]
      if (rR === bgR && rG === bgG && rB === bgB) continue
      totalPixels++
      const vR = vd[i], vG = vd[i+1], vB = vd[i+2]
      const dist = oklabDist(toOklab(rR, rG, rB), toOklab(vR, vG, vB))
      if (dist > MISMATCH_THRESHOLD) mismatchedPixels++
    }
    const score = totalPixels === 0 ? 0 : mismatchedPixels / totalPixels
    return { score, mismatchedPixels, totalPixels }
  })
}