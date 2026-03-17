import { Download, GripVertical } from 'lucide-react'
import { ZoomableImage } from './ZoomableImage'
import { PaletteStrip } from './PaletteStrip'
import './ItemCard.css'

function downloadPal(palContent, filename) {
  const blob = new Blob([palContent], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename.endsWith('.pal') ? filename : `${filename}.pal`
  a.click()
}

export function ItemCard({ result, isReference, listMode, groupId }) {
  const handleDragStart = (e) => {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ spriteName: result.name, fromGroupId: groupId }))
  }

  return (
    <div
      className={`item-card ${isReference ? 'is-reference' : ''} ${listMode ? 'list-mode' : ''}`}
      draggable
      onDragStart={handleDragStart}
    >
      <div className="item-drag-handle" title="drag to move to another group">
        <GripVertical size={12} />
      </div>

      {listMode ? (
        <>
          <div className="item-card-preview">
            <ZoomableImage src={result.preview} alt={result.name} />
          </div>
          <div className="item-card-body">
            <div className="item-card-header">
              <span className="item-card-name">{result.name}</span>
              {isReference && <span className="item-card-ref-badge">ref</span>}
              <button className="sprite-queue-btn"
                onClick={() => downloadPal(result.pal_content, result.name)}>
                <Download size={11} />
              </button>
            </div>
            <PaletteStrip colors={result.colors} usedIndices={result.colors.map((_, i) => i)} checkSize="50%" />
          </div>
        </>
      ) : (
        <>
          <div className="item-card-header">
            <span className="item-card-name">{result.name}</span>
            {isReference && <span className="item-card-ref-badge">ref</span>}
          </div>
          <PaletteStrip colors={result.colors} usedIndices={result.colors.map((_, i) => i)} checkSize="100%" />
          <ZoomableImage src={result.preview} alt={result.name} />
          <button className="btn-secondary" onClick={() => downloadPal(result.pal_content, result.name)}>
            <Download size={11} /> download .pal
          </button>
        </>
      )}
    </div>
  )
}