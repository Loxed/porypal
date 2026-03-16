import './ColorSwatch.css'

export function ColorSwatch({ hex }) {
  return (
    <span
      className="inline-swatch"
      style={{ background: hex }}
      title={hex}
    />
  )
}