import { useState, useEffect } from 'react'
import './ResultCard.css'
import { ZoomableImage } from './ZoomableImage'
import { PaletteStrip } from './PaletteStrip'
import { WalkAnimation } from './WalkAnimation'
import { splitFrames } from '../utils'

function detectOWSprite(b64) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => resolve(img.width / img.height >= 7.5 && img.width / img.height <= 10.5)
    img.src = `data:image/png;base64,${b64}`
  })
}

function FramesSection({ b64, frameCount, setFrameCount }) {
  const [frames, setFrames] = useState(null)
  const [show, setShow] = useState(false)

  const handleSplit = async (e) => {
    e.stopPropagation()
    const f = await splitFrames(b64, frameCount)
    setFrames(f); setShow(true)
  }

  return (
    <>
      <div className="frames-row" onClick={e => e.stopPropagation()}>
        <div className="split-row">
          <input type="number" min={1} max={32} value={frameCount}
            className="frame-count-input" title="frame count"
            onChange={e => setFrameCount(Number(e.target.value))} />
          <button className="btn-split" onClick={handleSplit}>
            {show ? 'refresh' : 'show frames'}
          </button>
          {show && <button className="btn-ghost" onClick={e => { e.stopPropagation(); setShow(false) }}>hide</button>}
        </div>
      </div>
      {show && frames && (
        <div className="frames-section" onClick={e => e.stopPropagation()}>
          <p className="section-label">frames ({frames.length})</p>
          <div className="frame-strip">
            {frames.map((f, i) => (
              <div key={i} className="frame-cell">
                <img src={`data:image/png;base64,${f}`} alt={`frame ${i}`}
                  className="pixel-img frame-img" draggable={false} />
                <span className="frame-index">{i}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

export function ResultCard({ result, selected, onSelect, onDownload, listMode = false }) {
  const [frameCount, setFrameCount] = useState(9)
  const [isOWSprite, setIsOWSprite] = useState(false)

  useEffect(() => {
    detectOWSprite(result.image).then(setIsOWSprite)
  }, [result.image])

  const colorsLabel = `${result.colors_used}/16`

  if (listMode) {
    return (
      <div
        className={`result-card list-mode ${selected ? 'selected' : ''} ${result.best ? 'best' : ''}`}
        onClick={onSelect}
      >
        {/* row 1: name -- colors -- best tag -- palette strip -- download */}
        <div className="list-row-1" onClick={e => e.stopPropagation()}>
          <span className="result-name">{result.palette_name.replace('.pal', '')}</span>
          <span className="result-colors">{colorsLabel} colors</span>
          <div className="list-palette">
            <PaletteStrip colors={result.colors} usedIndices={result.used_indices} checkSize="50%" />
          </div>
          <button className="btn-download"
            onClick={e => { e.stopPropagation(); onDownload(result.palette_name) }}>
            download
          </button>
        </div>

        {/* row 2: animation + zoom */}
        <div className="list-row-2">
          {isOWSprite && <WalkAnimation spriteB64={result.image} />}
          <div className="list-zoom">
            <ZoomableImage src={result.image} alt={result.palette_name} />
          </div>
        </div>

        {/* row 3: frames */}
        {isOWSprite && (
          <FramesSection b64={result.image} frameCount={frameCount} setFrameCount={setFrameCount} />
        )}
      </div>
    )
  }

  // grid mode
  return (
    <div
      className={`result-card ${selected ? 'selected' : ''} ${result.best ? 'best' : ''}`}
      onClick={onSelect}
    >
      {/* row 1: name -- colors -- best tag inline */}
      <div className="result-header">
        <span className="result-name">{result.palette_name.replace('.pal', '')}</span>
        <span className="result-colors">{colorsLabel} colors</span>
      </div>

      {/* row 2: palette strip */}
      <PaletteStrip colors={result.colors} usedIndices={result.used_indices} checkSize="100%" />

      {/* row 3: full-width zoomable image */}
      <ZoomableImage src={result.image} alt={result.palette_name} />

      {/* row 4: animation */}
      {isOWSprite && <WalkAnimation spriteB64={result.image} />}

      {/* row 5: frames + download */}
      <div className="grid-footer" onClick={e => e.stopPropagation()}>
        {isOWSprite && (
          <FramesSection b64={result.image} frameCount={frameCount} setFrameCount={setFrameCount} />
        )}
        <button className="btn-download full-width"
          onClick={e => { e.stopPropagation(); onDownload(result.palette_name) }}>
          download
        </button>
      </div>
    </div>
  )
}