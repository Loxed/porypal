import { Grid, List } from 'lucide-react'
import './ViewToggle.css'

/**
 * Grid / list view toggle.
 *
 * Props:
 *   value     {'grid' | 'list'}   current mode
 *   onChange  {fn}                (mode) => void
 */
export function ViewToggle({ value, onChange }) {
  return (
    <div className="view-toggle">
      <button
        className={`view-btn ${value === 'grid' ? 'active' : ''}`}
        title="grid view"
        onClick={() => onChange('grid')}
      >
        <Grid size={12} />
      </button>
      <button
        className={`view-btn ${value === 'list' ? 'active' : ''}`}
        title="list view"
        onClick={() => onChange('list')}
      >
        <List size={12} />
      </button>
    </div>
  )
}