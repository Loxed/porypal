import { useEffect } from 'react'
import { X } from 'lucide-react'
import './Modal.css'

/**
 * Shared modal shell. Drop any content inside as children.
 *
 * Props:
 *   title       {string}     shown in the header
 *   onClose     {fn}         called when backdrop or X button is clicked
 *   size        {string?}    'sm' | 'lg' | 'xl' | undefined (default ~480px)
 *   actions     {ReactNode?} extra buttons in the header, right of the title
 *   children    {ReactNode}  modal body content
 */
export function Modal({ title, onClose, size, actions, children }) {
  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className={`modal-box ${size ? `modal-${size}` : ''}`}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <span className="modal-title">{title}</span>
          {actions && <div className="modal-header-actions">{actions}</div>}
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  )
}