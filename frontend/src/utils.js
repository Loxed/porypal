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