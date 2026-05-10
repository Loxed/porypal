import { useState, useEffect, useRef } from 'react'
import './TilesetTab.css'
import { DropZone } from '../components/DropZone'
import { Modal } from '../components/Modal'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob } from '../utils'
import { Info, X, Save, Download, FlipHorizontal2, FlipVertical2, RotateCwSquare, RotateCcwSquare } from 'lucide-react'
import { PresetList } from '../components/PresetList'

const API = '/api'

const OW_LABELS = [
  'down idle','up idle','left idle',
  'down walk 1','down walk 2',
  'up walk 1','up walk 2',
  'left walk 1','left walk 2',
]

function useDebounce(value, delay) {
  const [d, setD] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setD(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return d
}

function getSlotKey(row, col) {
  return `${row}:${col}`
}

function cacheSlots(slots, cols, rows) {
  const next = new Map()
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      next.set(getSlotKey(row, col), slots[row * cols + col] ?? null)
    }
  }
  return next
}

function mergeSlotsIntoCache(cache, slots, cols, rows) {
  const next = new Map(cache)
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      next.set(getSlotKey(row, col), slots[row * cols + col] ?? null)
    }
  }
  return next
}

function slotsFromCache(cache, cols, rows) {
  const next = Array(cols * rows).fill(null)
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      next[row * cols + col] = cache.get(getSlotKey(row, col)) ?? null
    }
  }
  return next
}

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function remapGrid(items, cols, rows, nextCols, nextRows, mapper) {
  const next = Array(nextCols * nextRows).fill(null)
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const target = mapper(row, col)
      if (!target) continue
      const { row: nextRow, col: nextCol } = target
      next[nextRow * nextCols + nextCol] = items[row * cols + col] ?? null
    }
  }
  return next
}

function reorderRowsFlat(items, cols, rows, from, to) {
  const gridRows = Array.from({ length: rows }, (_, row) => items.slice(row * cols, (row + 1) * cols))
  const [picked] = gridRows.splice(from, 1)
  gridRows.splice(to, 0, picked)
  return gridRows.flat()
}

function reorderColsFlat(items, cols, rows, from, to) {
  const next = Array(cols * rows).fill(null)
  const order = Array.from({ length: cols }, (_, col) => col)
  const [picked] = order.splice(from, 1)
  order.splice(to, 0, picked)
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      next[row * cols + col] = items[row * cols + order[col]] ?? null
    }
  }
  return next
}

function swapRowsFlat(items, cols, rows, first, second) {
  const next = [...items]
  for (let col = 0; col < cols; col += 1) {
    const firstIdx = first * cols + col
    const secondIdx = second * cols + col
    ;[next[firstIdx], next[secondIdx]] = [next[secondIdx], next[firstIdx]]
  }
  return next
}

function swapColsFlat(items, cols, rows, first, second) {
  const next = [...items]
  for (let row = 0; row < rows; row += 1) {
    const firstIdx = row * cols + first
    const secondIdx = row * cols + second
    ;[next[firstIdx], next[secondIdx]] = [next[secondIdx], next[firstIdx]]
  }
  return next
}

function flipRowFlat(items, cols, rowIndex) {
  const next = [...items]
  for (let col = 0; col < Math.floor(cols / 2); col += 1) {
    const leftIdx = rowIndex * cols + col
    const rightIdx = rowIndex * cols + (cols - col - 1)
    ;[next[leftIdx], next[rightIdx]] = [next[rightIdx], next[leftIdx]]
  }
  return next
}

function flipColFlat(items, cols, rows, colIndex) {
  const next = [...items]
  for (let row = 0; row < Math.floor(rows / 2); row += 1) {
    const topIdx = row * cols + colIndex
    const bottomIdx = (rows - row - 1) * cols + colIndex
    ;[next[topIdx], next[bottomIdx]] = [next[bottomIdx], next[topIdx]]
  }
  return next
}

function NumberStepper({ value, min, max, onChange, className = 'field-input' }) {
  const [draft, setDraft] = useState(String(value))

  useEffect(() => {
    setDraft(String(value))
  }, [value])

  const applyValue = (nextValue) => {
    if (Number.isNaN(nextValue)) return
    const clamped = clampNumber(nextValue, min, max)
    setDraft(String(clamped))
    onChange(clamped)
  }

  return (
    <div className="number-stepper">
      <input
        type="number"
        className={className}
        min={min}
        max={max}
        value={draft}
        onChange={e => {
          const nextDraft = e.target.value
          setDraft(nextDraft)
          if (nextDraft === '') return
          applyValue(Number(nextDraft))
        }}
        onBlur={() => {
          if (draft === '') {
            setDraft(String(value))
            return
          }
          applyValue(Number(draft))
        }}
      />
      <button
        type="button"
        className="number-stepper-btn number-stepper-btn--left"
        onClick={() => applyValue(value + 1)}
        aria-label="Increase value"
      >
        +
      </button>
      <button
        type="button"
        className="number-stepper-btn number-stepper-btn--right"
        onClick={() => applyValue(value - 1)}
        aria-label="Decrease value"
      >
        -
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Help modal
// ---------------------------------------------------------------------------
function HelpModal({ onClose }) {
  return (
    <Modal title="Overworld sprite format" onClose={onClose}>
      <p className="modal-desc">Gen 3 overworld sprites are 9-frame spritesheets arranged horizontally:</p>
      <div className="frame-reference">
        {OW_LABELS.map((label, i) => (
          <div key={i} className="frame-ref-row">
            <span className="frame-ref-idx">{i}</span>
            <span className="frame-ref-label">{label}</span>
          </div>
        ))}
      </div>
      <p className="modal-note">Right-facing frames are generated by flipping left-facing frames at runtime.</p>
      <div className="modal-examples">
        <p className="section-label" style={{ marginBottom: 8 }}>examples</p>
        <div className="example-imgs">
          <div className="example-img-wrap">
            <img src="/img/help/tileset/cynthia.png" alt="NDS styled sprite" className="example-img" draggable={false}/>
            <span className="example-caption">cynthia.png</span>
          </div>
          <div className="example-img-wrap">
            <img src="/img/help/tileset/may.png" alt="GBA styled sprite" className="example-img" draggable={false}/>
            <span className="example-caption">may.png</span>
          </div>
        </div>
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Save preset modal
// ---------------------------------------------------------------------------
function SaveModal({ onSave, onClose }) {
  const [name, setName] = useState('')
  const [id, setId]     = useState('')
  return (
    <Modal title="save preset" onClose={onClose} size="sm">
      <div className="field">
        <label className="field-label">name</label>
        <input className="field-input" value={name}
          onChange={e => {
            setName(e.target.value)
            setId(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,''))
          }}
          placeholder="My custom preset" />
      </div>
      <div className="field">
        <label className="field-label">id</label>
        <input className="field-input field-mono" value={id}
          onChange={e => setId(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g,''))}
          placeholder="my_custom_preset" />
      </div>
      <button className="btn-primary" disabled={!name || !id} onClick={() => onSave(id, name)}>save</button>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Source sheet with tile grid overlay
// ---------------------------------------------------------------------------
function SourceSheet({ b64, sourceW, sourceH, tileW, tileH, selectedTile, onTileClick }) {
  if (!b64) return null
  const cols  = Math.max(1, Math.floor(sourceW / tileW))
  const rows  = Math.max(1, Math.floor(sourceH / tileH))
  return (
    <div className="source-sheet-wrap">
      <div className="source-grid-container">
        <img src={`data:image/png;base64,${b64}`} alt="source" className="source-img" draggable={false}/>
        <div className="source-tile-grid" style={{ '--src-cols': cols, '--src-rows': rows }}>
          {Array.from({ length: cols * rows }).map((_, idx) => (
            <div
              key={idx}
              className={`source-tile ${selectedTile === idx ? 'selected' : ''}`}
              onClick={() => onTileClick(idx)}
              title={`tile ${idx}`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Output slot grid
// ---------------------------------------------------------------------------
function OutputGrid({
  slots, setVisibleSlots, cols, rows, tiles, selectedTile, setSelectedTile, slotLabels,
  pendingRowAction, pendingColAction, onStartRowAction, onStartColAction, onCompleteRowAction, onCompleteColAction,
  onReorderRows, onReorderCols, onFlipRow, onFlipCol,
}) {
  const [hoveredRow, setHoveredRow] = useState(null)
  const [hoveredCol, setHoveredCol] = useState(null)
  const [dragState, setDragState] = useState(null)
  const [dragTarget, setDragTarget] = useState(null)
  const [isPainting, setIsPainting] = useState(false)
  const placeTileAt = (idx) => {
    if (selectedTile == null) return
    setVisibleSlots(prev => {
      if (prev[idx] === selectedTile) return prev
      const next = [...prev]
      next[idx] = selectedTile
      return next
    })
  }
  const handleSlotClick = (idx) => {
    if (selectedTile == null && slots[idx] != null) {
      setSelectedTile(slots[idx])
      setVisibleSlots(prev => { const s = [...prev]; s[idx] = null; return s })
    }
  }
  useEffect(() => {
    const handleMouseUp = () => setIsPainting(false)
    window.addEventListener('mouseup', handleMouseUp)
    return () => window.removeEventListener('mouseup', handleMouseUp)
  }, [])
  const clearSlot = (e, idx) => {
    e.stopPropagation()
    setVisibleSlots(prev => { const s = [...prev]; s[idx] = null; return s })
  }
  const canPlace = selectedTile !== null
  const previewSlots = dragState && dragTarget != null && dragState.index !== dragTarget
    ? (dragState.axis === 'row'
      ? reorderRowsFlat(slots, cols, rows, dragState.index, dragTarget)
      : reorderColsFlat(slots, cols, rows, dragState.index, dragTarget))
    : slots
  const previewLabels = dragState && dragTarget != null && dragState.index !== dragTarget && slotLabels?.length === cols * rows
    ? (dragState.axis === 'row'
      ? reorderRowsFlat(slotLabels, cols, rows, dragState.index, dragTarget)
      : reorderColsFlat(slotLabels, cols, rows, dragState.index, dragTarget))
    : slotLabels
  return (
    <div className="output-grid-shell" style={{ '--cols': cols, '--rows': rows }}>
      {cols > 1 && (
        <div className="output-col-actions">
          {Array.from({ length: cols }).map((_, col) => {
            const isArmed = pendingColAction?.index === col
            const isDropTarget = dragState?.axis === 'col' && dragTarget === col && dragState.index !== col
            return (
              <div
                key={col}
                className={`axis-action axis-action--col ${isArmed ? 'armed' : ''} ${pendingColAction ? 'targeting' : ''} ${isDropTarget ? 'drop-target' : ''}`}
                onMouseEnter={() => setHoveredCol(col)}
                onMouseLeave={() => setHoveredCol(prev => (prev === col ? null : prev))}
                onDragOver={(e) => {
                  if (dragState?.axis !== 'col') return
                  e.preventDefault()
                  setDragTarget(col)
                }}
                onDrop={(e) => {
                  if (dragState?.axis !== 'col') return
                  e.preventDefault()
                  onReorderCols(dragState.index, col)
                  setDragState(null)
                  setDragTarget(null)
                }}
              >
                <button
                  type="button"
                  className="axis-action-target"
                  onClick={() => pendingColAction ? onCompleteColAction(col) : null}
                  draggable={!pendingColAction}
                  onDragStart={() => {
                    setDragState({ axis: 'col', index: col })
                    setDragTarget(col)
                  }}
                  onDragEnd={() => {
                    setDragState(null)
                    setDragTarget(null)
                  }}
                >
                  {pendingColAction ? (isArmed ? pendingColAction.type : 'to') : `c${col + 1}`}
                </button>
                {!pendingColAction && (
                  <div className={`axis-action-menu ${dragState ? 'hidden' : ''}`}>
                    <button type="button" className="axis-action-btn" onClick={() => onStartColAction('duplicate', col)}>duplicate</button>
                    <button type="button" className="axis-action-btn" onClick={() => onStartColAction('swap', col)}>swap</button>
                    <button type="button" className="axis-action-btn" onClick={() => onFlipCol(col)}>flip</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {rows > 1 && (
        <div className="output-row-actions">
          {Array.from({ length: rows }).map((_, row) => {
            const isArmed = pendingRowAction?.index === row
            const isDropTarget = dragState?.axis === 'row' && dragTarget === row && dragState.index !== row
            return (
              <div
                key={row}
                className={`axis-action axis-action--row ${isArmed ? 'armed' : ''} ${pendingRowAction ? 'targeting' : ''} ${isDropTarget ? 'drop-target' : ''}`}
                onMouseEnter={() => setHoveredRow(row)}
                onMouseLeave={() => setHoveredRow(prev => (prev === row ? null : prev))}
                onDragOver={(e) => {
                  if (dragState?.axis !== 'row') return
                  e.preventDefault()
                  setDragTarget(row)
                }}
                onDrop={(e) => {
                  if (dragState?.axis !== 'row') return
                  e.preventDefault()
                  onReorderRows(dragState.index, row)
                  setDragState(null)
                  setDragTarget(null)
                }}
              >
                <button
                  type="button"
                  className="axis-action-target"
                  onClick={() => pendingRowAction ? onCompleteRowAction(row) : null}
                  draggable={!pendingRowAction}
                  onDragStart={() => {
                    setDragState({ axis: 'row', index: row })
                    setDragTarget(row)
                  }}
                  onDragEnd={() => {
                    setDragState(null)
                    setDragTarget(null)
                  }}
                >
                  {pendingRowAction ? (isArmed ? pendingRowAction.type : 'to') : `r${row + 1}`}
                </button>
                {!pendingRowAction && (
                  <div className={`axis-action-menu ${dragState ? 'hidden' : ''}`}>
                    <button type="button" className="axis-action-btn" onClick={() => onStartRowAction('duplicate', row)}>duplicate</button>
                    <button type="button" className="axis-action-btn" onClick={() => onStartRowAction('swap', row)}>swap</button>
                    <button type="button" className="axis-action-btn" onClick={() => onFlipRow(row)}>flip</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <div className="output-grid" style={{ '--cols': cols, '--rows': rows }}>
        {Array.from({ length: cols * rows }).map((_, idx) => {
          const tileIdx = previewSlots[idx]
          const hasTile = tileIdx != null
          const label   = previewLabels?.[idx] ?? String(idx)
          const row     = Math.floor(idx / cols)
          const col     = idx % cols
          return (
            <div
              key={idx}
              className={`output-slot ${hasTile ? 'filled' : 'empty'} ${canPlace && !hasTile ? 'droppable' : ''} ${hoveredRow === row || hoveredCol === col ? 'axis-hovered' : ''} ${dragState?.axis === 'row' && dragTarget === row ? 'axis-previewed' : ''} ${dragState?.axis === 'col' && dragTarget === col ? 'axis-previewed' : ''}`}
              onClick={() => handleSlotClick(idx)}
              onMouseDown={(e) => {
                if (e.button !== 0 || selectedTile == null) return
                e.preventDefault()
                placeTileAt(idx)
                setIsPainting(true)
              }}
              onMouseEnter={() => {
                if (!isPainting || selectedTile == null) return
                placeTileAt(idx)
              }}
            >
              {hasTile && tiles?.[tileIdx]
                ? <img src={`data:image/png;base64,${tiles[tileIdx]}`} alt={label} className="slot-img" draggable={false}/>
                : <span className="slot-plus">+</span>
              }
              <span className="slot-label">{label}</span>
              {hasTile && (
                <button className="slot-clear" onClick={e => clearSlot(e, idx)}><X size={9}/></button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Download via backend so indexed PNG metadata can be preserved
// ---------------------------------------------------------------------------
async function buildAndDownload(sourceFile, slots, cols, rows, inputTileW, inputTileH, outputTileW, outputTileH, filename) {
  if (!sourceFile) throw new Error('No tileset source available')

  const fd = new FormData()
  fd.append('file', sourceFile)
  fd.append('input_tile_width', String(inputTileW))
  fd.append('input_tile_height', String(inputTileH))
  fd.append('output_tile_width', String(outputTileW))
  fd.append('output_tile_height', String(outputTileH))
  fd.append('cols', String(cols))
  fd.append('rows', String(rows))
  fd.append('sprite_order', slots.map(tileIdx => (tileIdx == null ? '' : String(tileIdx))).join(','))

  const res = await fetch(`${API}/tileset/arrange`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error(await res.text())

  const blob = await res.blob()
  downloadBlob(blob, filename)
}

// ---------------------------------------------------------------------------
// Main tab
// ---------------------------------------------------------------------------
export function TilesetTab() {
  const [file, setFile]         = useState(null)
  const [arrangeFile, setArrangeFile] = useState(null)
  const [outputName, setOutputName] = useState('')
  // Source tile size (how big tiles are in the uploaded image)
  const [inTileW, setInTileW]   = useState(32)
  const [inTileH, setInTileH]   = useState(32)
  // Output tile size (what size tiles should be in the result)
  const [outTileW, setOutTileW] = useState(32)
  const [outTileH, setOutTileH] = useState(32)
  const [cols, setCols]         = useState(9)
  const [rows, setRows]         = useState(1)
  const [slotLabels, setSlotLabels] = useState([])

  const [result, setResult]               = useState(null)
  const [slots, setSlots]                 = useState(Array(9).fill(null))
  const [selectedTile, setSelectedTile]   = useState(null)
  const [showHelp, setShowHelp]           = useState(false)
  const [showSave, setShowSave]           = useState(false)
  const [presets, setPresets]             = useState([])
  const [activePresetId, setActivePresetId] = useState(null)
  const [defaultIds, setDefaultIds]       = useState(new Set())
  const [downloadError, setDownloadError] = useState(null)
  const [downloading, setDownloading]     = useState(false)
  const [pendingRowAction, setPendingRowAction] = useState(null)
  const [pendingColAction, setPendingColAction] = useState(null)
  const { loading, error, run }           = useFetch()
  const slotCacheRef                      = useRef(cacheSlots(Array(9).fill(null), 9, 1))

  // Debounce everything that triggers a re-slice
  const dInW  = useDebounce(inTileW,  500)
  const dInH  = useDebounce(inTileH,  500)
  const dOutW = useDebounce(outTileW, 500)
  const dOutH = useDebounce(outTileH, 500)

  const fetchPresets = () =>
    fetch(`${API}/presets`).then(r => r.json()).then(p => {
      setPresets(p)
      setDefaultIds(new Set(p.filter(x => x.is_default).map(x => x.id)))
    }).catch(() => {})

  useEffect(() => { fetchPresets() }, [])

  useEffect(() => {
    if (file) doSlice(file, dInW, dInH, dOutW, dOutH)
  }, [dInW, dInH, dOutW, dOutH])

  useEffect(() => {
    if (pendingRowAction && pendingRowAction.index >= rows) setPendingRowAction(null)
  }, [rows, pendingRowAction])

  useEffect(() => {
    if (pendingColAction && pendingColAction.index >= cols) setPendingColAction(null)
  }, [cols, pendingColAction])

  const resetSlots = (c, r) => {
    const nextSlots = Array(c * r).fill(null)
    slotCacheRef.current = cacheSlots(nextSlots, c, r)
    setSlots(nextSlots)
  }

  const setVisibleSlots = (updater, nextCols = cols, nextRows = rows) => {
    setSlots(prev => {
      const nextSlots = typeof updater === 'function' ? updater(prev) : updater
      slotCacheRef.current = mergeSlotsIntoCache(slotCacheRef.current, nextSlots, nextCols, nextRows)
      return nextSlots
    })
  }

  const resizeLayout = (nextCols, nextRows) => {
    slotCacheRef.current = mergeSlotsIntoCache(slotCacheRef.current, slots, cols, rows)
    setCols(nextCols)
    setRows(nextRows)
    setSlots(slotsFromCache(slotCacheRef.current, nextCols, nextRows))
  }

  const applyLayoutChange = (transformSlots, options = {}) => {
    const nextCols = options.nextCols ?? cols
    const nextRows = options.nextRows ?? rows
    const nextSlots = transformSlots(slots)
    slotCacheRef.current = cacheSlots(nextSlots, nextCols, nextRows)
    setSlots(nextSlots)
    setPendingRowAction(null)
    setPendingColAction(null)
    if (options.transformLabels) {
      setSlotLabels(prev => (
        prev.length === cols * rows
          ? options.transformLabels(prev)
          : prev
      ))
    }
    if (nextCols !== cols) setCols(nextCols)
    if (nextRows !== rows) setRows(nextRows)
  }

  // ---------------------------------------------------------------------------
  // Slice on the backend so paletted PNG metadata can be preserved
  // ---------------------------------------------------------------------------
  const doSlice = async (f, iw, ih, ow, oh) => {
    setArrangeFile(f)

    const fd = new FormData()
    fd.append('file', f)
    fd.append('input_tile_width', String(iw))
    fd.append('input_tile_height', String(ih))
    fd.append('output_tile_width', String(ow))
    fd.append('output_tile_height', String(oh))

    const data = await run(async () => {
      const res = await fetch(`${API}/tileset/slice`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) { setResult(data); setSelectedTile(null) }
  }

  const handleFile = (f) => {
    setFile(f); setArrangeFile(f); setResult(null); resetSlots(cols, rows); setDownloadError(null)
    setOutputName(`${f.name.replace(/\.[^.]+$/, '')}_arranged`)
    doSlice(f, inTileW, inTileH, outTileW, outTileH)
  }

  const handleColsChange = (v) => resizeLayout(v, rows)
  const handleRowsChange = (v) => resizeLayout(cols, v)
  const handleTransposeLayout = () => {
    const nextCols = rows
    const nextRows = cols
    const transposeGrid = items => remapGrid(items, cols, rows, nextCols, nextRows, (row, col) => ({ row: col, col: row }))
    applyLayoutChange(transposeGrid, { nextCols, nextRows, transformLabels: transposeGrid })
  }

  const handleFlipHorizontal = () => {
    const flip = items => remapGrid(items, cols, rows, cols, rows, (row, col) => ({ row, col: cols - col - 1 }))
    applyLayoutChange(flip, { transformLabels: flip })
  }

  const handleFlipVertical = () => {
    const flip = items => remapGrid(items, cols, rows, cols, rows, (row, col) => ({ row: rows - row - 1, col }))
    applyLayoutChange(flip, { transformLabels: flip })
  }

  const handleRotateClockwise = () => {
    const nextCols = rows
    const nextRows = cols
    const rotate = items => remapGrid(items, cols, rows, nextCols, nextRows, (row, col) => ({ row: col, col: rows - row - 1 }))
    applyLayoutChange(rotate, { nextCols, nextRows, transformLabels: rotate })
  }

  const handleRotateCounterClockwise = () => {
    const nextCols = rows
    const nextRows = cols
    const rotate = items => remapGrid(items, cols, rows, nextCols, nextRows, (row, col) => ({ row: cols - col - 1, col: row }))
    applyLayoutChange(rotate, { nextCols, nextRows, transformLabels: rotate })
  }

  const runRowAction = (type, from, to) => {
    const transform = (items) => {
      if (type === 'duplicate') {
        const next = [...items]
        for (let col = 0; col < cols; col += 1) {
          next[to * cols + col] = items[from * cols + col] ?? null
        }
        return next
      }
      return swapRowsFlat(items, cols, rows, from, to)
    }
    applyLayoutChange(transform, { transformLabels: transform })
  }

  const runColAction = (type, from, to) => {
    const transform = (items) => {
      if (type === 'duplicate') {
        const next = [...items]
        for (let row = 0; row < rows; row += 1) {
          next[row * cols + to] = items[row * cols + from] ?? null
        }
        return next
      }
      return swapColsFlat(items, cols, rows, from, to)
    }
    applyLayoutChange(transform, { transformLabels: transform })
  }

  const handleReorderRows = (from, to) => {
    if (from === to) return
    const reorder = items => reorderRowsFlat(items, cols, rows, from, to)
    applyLayoutChange(reorder, { transformLabels: reorder })
  }

  const handleReorderCols = (from, to) => {
    if (from === to) return
    const reorder = items => reorderColsFlat(items, cols, rows, from, to)
    applyLayoutChange(reorder, { transformLabels: reorder })
  }

  const handleFlipRow = (rowIndex) => {
    const flip = items => flipRowFlat(items, cols, rowIndex)
    applyLayoutChange(flip, { transformLabels: flip })
  }

  const handleFlipCol = (colIndex) => {
    const flip = items => flipColFlat(items, cols, rows, colIndex)
    applyLayoutChange(flip, { transformLabels: flip })
  }

  const handleStartRowAction = (type, index) => {
    setPendingColAction(null)
    setPendingRowAction({ type, index })
  }

  const handleStartColAction = (type, index) => {
    setPendingRowAction(null)
    setPendingColAction({ type, index })
  }

  const handleCompleteRowAction = (targetIndex) => {
    if (!pendingRowAction) return
    runRowAction(pendingRowAction.type, pendingRowAction.index, targetIndex)
  }

  const handleCompleteColAction = (targetIndex) => {
    if (!pendingColAction) return
    runColAction(pendingColAction.type, pendingColAction.index, targetIndex)
  }

  const handleCancelAxisAction = () => {
    setPendingRowAction(null)
    setPendingColAction(null)
  }

  // Sync outTileW/H when in changes (unless user has already diverged them)
  const handleInTileW = (v) => {
    if (inTileW === outTileW) setOutTileW(v)
    setInTileW(v)
  }
  const handleInTileH = (v) => {
    if (inTileH === outTileH) setOutTileH(v)
    setInTileH(v)
  }

  // ---------------------------------------------------------------------------
  // Presets
  // ---------------------------------------------------------------------------
  const handleLoadPreset = async (id) => {
    const p = await fetch(`${API}/presets/${id}`).then(r => r.json())
    setInTileW(p.tile_w);   setInTileH(p.tile_h)
    setOutTileW(p.out_tile_w ?? p.tile_w)
    setOutTileH(p.out_tile_h ?? p.tile_h)
    const presetSlots = p.slots?.length === p.cols * p.rows ? p.slots : Array(p.cols * p.rows).fill(null)
    setCols(p.cols);         setRows(p.rows)
    slotCacheRef.current = cacheSlots(presetSlots, p.cols, p.rows)
    setSlots(presetSlots)
    setSlotLabels(p.slot_labels || [])
    setActivePresetId(id)
    if (file) doSlice(file, p.tile_w, p.tile_h, p.out_tile_w ?? p.tile_w, p.out_tile_h ?? p.tile_h)
  }

  const handleSavePreset = async (id, name) => {
    const srcCols = result ? Math.floor(result.source_w / result.input_tile_width)  : undefined
    const srcRows = result ? Math.floor(result.source_h / result.input_tile_height) : undefined
    const body = {
      name,
      tile_w:     inTileW,
      tile_h:     inTileH,
      out_tile_w: outTileW,
      out_tile_h: outTileH,
      cols, rows, slots,
      slot_labels: slotLabels.length ? slotLabels : undefined,
      src_cols:   srcCols,
      src_rows:   srcRows,
    }
    await fetch(`${API}/presets/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    fetchPresets(); setActivePresetId(id); setShowSave(false)
  }

  const handleDeletePreset = async (id) => {
    if (defaultIds.has(id)) return
    await fetch(`${API}/presets/${id}`, { method: 'DELETE' })
    fetchPresets()
    if (activePresetId === id) setActivePresetId(null)
  }

  const needsScale  = inTileW !== outTileW || inTileH !== outTileH
  const scaleLabel  = needsScale
    ? `${inTileW}×${inTileH} → ${outTileW}×${outTileH}`
    : `${outTileW}×${outTileH}px`

  const handleDownload = async () => {
    if (!result || !arrangeFile || slots.every(s => s == null) || !outputName.trim()) return
    setDownloadError(null)
    setDownloading(true)
    try {
      await buildAndDownload(
        arrangeFile, slots, cols, rows,
        result.input_tile_width, result.input_tile_height,
        result.tile_width, result.tile_height,
        `${outputName.trim()}.png`,
      )
    } catch (e) {
      setDownloadError(e.message || 'Failed to download arranged tileset')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="tab-content">
      {showHelp && <HelpModal onClose={() => setShowHelp(false)}/>}
      {showSave && <SaveModal onSave={handleSavePreset} onClose={() => setShowSave(false)}/>}

      <div className="tileset-layout">

        {/* ── Left panel ── */}
        <div className="tileset-left">
          <DropZone onFile={handleFile} label="Drop tileset image"/>

          {file && (
            <div className="field">
              <label className="field-label">output name</label>
              <input
                className="field-input"
                value={outputName}
                onChange={e => setOutputName(e.target.value)}
                spellCheck={false}
                placeholder="sprite_arranged"
              />
              <span className="tileset-field-hint">used for the downloaded PNG filename</span>
            </div>
          )}

          {/* Tile dimensions */}
          <div className="tile-dim-grid">
            <span className="tile-dim-label">input tile</span>
            <NumberStepper min={1} max={512} value={inTileW} onChange={handleInTileW} />
            <span className="tile-dim-sep">×</span>
            <NumberStepper min={1} max={512} value={inTileH} onChange={handleInTileH} />

            <span className="tile-dim-label">output tile</span>
            <NumberStepper
              min={1}
              max={512}
              className={`field-input ${needsScale ? 'field-input--accent' : ''}`}
              value={outTileW}
              onChange={setOutTileW}
            />
            <span className="tile-dim-sep">×</span>
            <NumberStepper
              min={1}
              max={512}
              className={`field-input ${needsScale ? 'field-input--accent' : ''}`}
              value={outTileH}
              onChange={setOutTileH}
            />
          </div>

          {/* Quick scale buttons — only shown when tiles differ */}
          {needsScale && (
            <div className="tile-quick-row">
              {[0.25, 0.5, 1, 2, 4].map(f => (
                <button key={f} className="tile-quick-btn"
                  onClick={() => { setOutTileW(Math.max(1,Math.round(inTileW*f))); setOutTileH(Math.max(1,Math.round(inTileH*f))) }}>
                  {f < 1 ? `${f}×` : `${f}×`}
                </button>
              ))}
              <button className="tile-quick-btn tile-quick-btn--reset"
                onClick={() => { setOutTileW(inTileW); setOutTileH(inTileH) }}>
                reset
              </button>
            </div>
          )}

          {/* Cols / rows */}
          <div className="tile-dim-grid">
            <span className="tile-dim-label">cols</span>
            <NumberStepper min={1} max={32} value={cols} onChange={handleColsChange} />
            <span className="tile-dim-sep"/>
            <span/>

            <span className="tile-dim-label">rows</span>
            <NumberStepper min={1} max={32} value={rows} onChange={handleRowsChange} />
            <span className="tile-dim-sep"/>
            <span/>
          </div>
          <div className="layout-tools-section">
            <p className="section-label">layout tools</p>
            <div className="layout-tool-grid">
              <button className="btn-secondary layout-tool-wide" onClick={handleTransposeLayout}>Transpose</button>
              <button className="btn-secondary layout-tool-icon-btn" onClick={handleFlipHorizontal} title="Flip horizontally">
                <FlipHorizontal2 size={20} />⠀Flip H
              </button>
              <button className="btn-secondary layout-tool-icon-btn" onClick={handleFlipVertical} title="Flip vertically">
                <FlipVertical2 size={20} />⠀Flip V
              </button>
              <button className="btn-secondary layout-tool-icon-btn" onClick={handleRotateClockwise} title="Rotate clockwise">
                <RotateCwSquare size={20} />⠀Rot CW
              </button>
              <button className="btn-secondary layout-tool-icon-btn" onClick={handleRotateCounterClockwise} title="Rotate counterclockwise">
                <RotateCcwSquare size={20} />⠀Rot CCW
              </button>
            </div>
            <span className="tileset-field-hint">grid operations live directly on the output surface</span>
          </div>

          {/* Presets */}
          <div className="preset-section">
            <p className="section-label">presets</p>
            <PresetList
              presets={presets}
              defaultIds={defaultIds}
              activePresetId={activePresetId}
              onLoad={handleLoadPreset}
              onDelete={handleDeletePreset}
              currentState={{ tileW: inTileW, tileH: inTileH, cols, rows, slots }}
            />
            <button className="btn-secondary preset-save-btn" onClick={() => setShowSave(true)}>
              <Save size={12}/> save as preset
            </button>
          </div>

          {(error || downloadError) && <p className="error-msg">{downloadError || error}</p>}

          {/* Source preview */}
          {result && (
            <div className="source-section">
              <p className="section-label">
                source — {result.tile_count} tiles
                {selectedTile !== null
                  ? <span className="selected-hint"> · {selectedTile} selected</span>
                  : <span className="selected-hint"> · click to select</span>
                }
              </p>
              <SourceSheet
                b64={result.source}
                sourceW={result.source_w}
                sourceH={result.source_h}
                tileW={result.input_tile_width}
                tileH={result.input_tile_height}
                selectedTile={selectedTile}
                onTileClick={i => setSelectedTile(prev => prev === i ? null : i)}
              />
            </div>
          )}
        </div>

        {/* ── Right panel ── */}
        <div className="tileset-right">
          <div className="tileset-toolbar">
            <span className="section-label">
              {result ? `output — ${cols}×${rows} · ${scaleLabel}` : 'no tileset loaded'}
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              {result && <>
                <button className="btn-ghost" onClick={() => resetSlots(cols, rows)}>clear</button>
              </>}
              <button className="tab-help-btn" onClick={() => setShowHelp(true)} title="Help"><Info size={15}/></button>
            </div>
          </div>

          {!result && !loading && <div className="empty-state"><p>drop a tileset to start arranging</p></div>}
          {loading && <div className="empty-state"><div className="spinner"/><p>slicing…</p></div>}

          {result && (
            <>
              {selectedTile !== null && (
                <div className="place-hint">
                  tile {selectedTile} selected — click or drag across slots to paint
                  <button className="btn-ghost" onClick={() => setSelectedTile(null)}>cancel</button>
                </div>
              )}
              {(pendingRowAction || pendingColAction) && (
                <div className="place-hint">
                  {pendingRowAction
                    ? `${pendingRowAction.type} row ${pendingRowAction.index + 1} — click a target row`
                    : `${pendingColAction.type} col ${pendingColAction.index + 1} — click a target col`
                  }
                  <button className="btn-ghost" onClick={handleCancelAxisAction}>cancel</button>
                </div>
              )}
              <div className="tileset-output-stack">
                <div className="tileset-grid-frame">
                  <OutputGrid
                    slots={slots} setVisibleSlots={setVisibleSlots}
                    cols={cols} rows={rows}
                    tiles={result.tiles}
                    selectedTile={selectedTile} setSelectedTile={setSelectedTile}
                    slotLabels={slotLabels}
                    pendingRowAction={pendingRowAction}
                    pendingColAction={pendingColAction}
                    onStartRowAction={handleStartRowAction}
                    onStartColAction={handleStartColAction}
                    onCompleteRowAction={handleCompleteRowAction}
                    onCompleteColAction={handleCompleteColAction}
                    onReorderRows={handleReorderRows}
                    onReorderCols={handleReorderCols}
                    onFlipRow={handleFlipRow}
                    onFlipCol={handleFlipCol}
                  />
                </div>
                <button
                  className="btn-primary tileset-download-btn"
                  disabled={slots.every(s => s == null) || !outputName.trim() || downloading}
                  onClick={handleDownload}
                >
                  <Download size={13} />
                  {downloading ? 'downloading…' : `Download '${outputName.trim()}.png'`}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
