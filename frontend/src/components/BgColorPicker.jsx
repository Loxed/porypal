import { Scan, Eclipse, PaintBucket, Pipette } from 'lucide-react'
import './BgColorPicker.css'

const GBA_TRANSPARENT = '#73C5A4'
const HEX_RE = /^#[0-9a-fA-F]{6}$/

/**
 * Reusable transparent-color picker used across Extract, Convert, Items, and Variants.
 *
 * Props:
 *   color            {string}   current hex value
 *   mode             {string}   'auto' | 'default' | 'custom' | 'pick'
 *   onChange         {fn}       ({color, mode}) => void  — every state change
 *   onCommit         {fn?}      (color) => void          — only on auto/default/valid blur
 *   showAuto         {bool?}    show the auto-detect button (default false)
 *   onAutoDetect     {fn?}      async () => string       — required when showAuto=true
 *   showPipette      {bool?}    show pipette toggle (default false)
 *   picking          {bool?}    pipette active state
 *   onPipetteToggle  {fn?}      () => void
 */
export function BgColorPicker({
  color,
  mode,
  onChange,
  onCommit,
  showAuto      = false,
  onAutoDetect,
  showPipette   = false,
  picking       = false,
  onPipetteToggle,
}) {
  const handleAuto = async () => {
    if (!onAutoDetect) return
    const detected = await onAutoDetect()
    onChange({ color: detected, mode: 'auto' })
    onCommit?.(detected)
  }

  const handleDefault = () => {
    onChange({ color: GBA_TRANSPARENT, mode: 'default' })
    onCommit?.(GBA_TRANSPARENT)
  }

  const handleCustom = () => {
    onChange({ color, mode: 'custom' })
  }

  const handleInput = e => {
    onChange({ color: e.target.value, mode: 'custom' })
  }

  const handleBlur = () => {
    if (HEX_RE.test(color)) onCommit?.(color)
  }

  const showInput = mode === 'custom' || mode === 'pick'

  return (
    <>
      <div className="bg-mode-row">
        {showAuto && (
          <button
            className={`bg-mode-btn ${mode === 'auto' ? 'active' : ''}`}
            onClick={handleAuto}
            title="detect from image corners"
          >
            auto <Scan size={8} />
          </button>
        )}
        <button
          className={`bg-mode-btn ${mode === 'default' ? 'active' : ''}`}
          onClick={handleDefault}
        >
          default <Eclipse size={8} />
        </button>
        <button
          className={`bg-mode-btn ${mode === 'custom' ? 'active' : ''}`}
          onClick={handleCustom}
        >
          custom <PaintBucket size={8} />
        </button>
        {showPipette && (
          <button
            className={`bg-mode-btn ${picking ? 'picking' : ''}`}
            onClick={onPipetteToggle}
            title="click a pixel on the image to pick its color"
          >
            pipette <Pipette size={8} />
          </button>
        )}
      </div>

      <div className="bg-color-row">
        <div className="bg-swatch" style={{ background: color }} />
        {showInput ? (
          <input
            className="field-input field-mono"
            value={color}
            onChange={handleInput}
            onBlur={handleBlur}
            placeholder="#73C5A4"
            maxLength={7}
          />
        ) : (
          <span className="bg-field-hint">
            {color}
            {mode === 'auto'    && <span className="bg-mode-tag"> auto-detected</span>}
            {mode === 'default' && <span className="bg-mode-tag"> GBA default</span>}
          </span>
        )}
      </div>
    </>
  )
}