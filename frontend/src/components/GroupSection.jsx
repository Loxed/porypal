import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronRight, Pencil, Merge } from 'lucide-react'
import { ItemCard } from './ItemCard'
import { SharedSlotsStrip } from './SharedSlotsStrip'
import './GroupSection.css'

// ---------------------------------------------------------------------------
// MergeDropdown — local to GroupSection, not worth its own file
// ---------------------------------------------------------------------------
function MergeDropdown({ thisGroupId, allGroups, groupNames, onMerge }) {
  const [open, setOpen] = useState(false)
  const ref = useRef()

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const others = allGroups.filter(g => g.group_id !== thisGroupId)
  if (others.length === 0) return null

  return (
    <div className="merge-dropdown" ref={ref}>
      <button
        className="group-action-btn"
        title="merge entire group into another"
        onClick={e => { e.stopPropagation(); setOpen(o => !o) }}
      >
        <Merge size={11} />
      </button>
      {open && (
        <div className="merge-menu">
          <p className="merge-menu-label">merge into…</p>
          {others.map(g => (
            <button key={g.group_id} className="merge-menu-item"
              onClick={e => { e.stopPropagation(); setOpen(false); onMerge(thisGroupId, g.group_id) }}>
              {groupNames[g.group_id] ?? g.group_id}
              <span className="merge-menu-meta">{g.results.length} sprites</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// GroupSection
// ---------------------------------------------------------------------------
export function GroupSection({
  group, groupName, onRename, onDropSprite, onMergeGroup,
  allGroups, groupNames,
  viewMode, exact, nUnique,
  sharedSlots, nShared,
}) {
  const [open, setOpen]         = useState(true)
  const [editing, setEditing]   = useState(false)
  const [nameVal, setNameVal]   = useState(groupName)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => { setNameVal(groupName) }, [groupName])

  const commitRename = () => {
    if (nameVal.trim()) onRename(nameVal.trim())
    else setNameVal(groupName)
    setEditing(false)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(true)
  }
  const handleDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragOver(false)
  }
  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (data.fromGroupId !== group.group_id) {
        onDropSprite(data.spriteName, data.fromGroupId, group.group_id)
      }
    } catch { /* ignore */ }
  }

  return (
    <div className={`group-section ${dragOver ? 'group-drop-target' : ''}`}>
      <div className="group-header"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <button className="group-collapse-btn" onClick={() => setOpen(o => !o)}>
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>

        {editing ? (
          <input className="group-name-input" value={nameVal}
            onChange={e => setNameVal(e.target.value)} onBlur={commitRename}
            onKeyDown={e => {
              if (e.key === 'Enter') commitRename()
              if (e.key === 'Escape') { setNameVal(groupName); setEditing(false) }
            }} autoFocus />
        ) : (
          <span className="group-name" onClick={() => setEditing(true)}>{groupName}</span>
        )}

        <span className="group-meta">
          {group.dimensions} · {group.results.length} sprite{group.results.length !== 1 ? 's' : ''}
          {' · '}
          {exact
            ? <span style={{ color: 'var(--best)' }}>{nUnique} colors · exact</span>
            : <span style={{ color: '#e3b341' }}>{nUnique} → {group.results[0]?.colors.length - 1} colors · clustered</span>
          }
        </span>

        <div className="group-actions">
          <button className="group-action-btn" title="rename" onClick={() => setEditing(true)}>
            <Pencil size={11} />
          </button>
          <MergeDropdown
            thisGroupId={group.group_id}
            allGroups={allGroups}
            groupNames={groupNames}
            onMerge={onMergeGroup}
          />
        </div>

        {dragOver && <span className="group-drop-hint">drop to merge</span>}
      </div>

      {open && sharedSlots && sharedSlots.length > 0 && (
        <SharedSlotsStrip sharedSlots={sharedSlots} nShared={nShared ?? 0} />
      )}

      {open && (
        <div className={viewMode === 'grid' ? 'items-results-grid' : 'items-results-list'}>
          {group.results.map(r => (
            <ItemCard
              key={r.name}
              result={r}
              isReference={r.name === group.reference}
              listMode={viewMode === 'list'}
              groupId={group.group_id}
            />
          ))}
        </div>
      )}
    </div>
  )
}