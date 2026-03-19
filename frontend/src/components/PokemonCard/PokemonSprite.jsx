import { useState } from 'react'

const API = '/api'

export function PokemonSprite({ path, className = '', style = {} }) {
  const [err, setErr] = useState(false)
  if (!path || err) return null
  return (
    <img
      className={`pkm-sprite ${className}`}
      src={`${API}/palette-library/sprite?path=${encodeURIComponent(path)}`}
      onError={() => setErr(true)}
      alt=""
      draggable={false}
      style={style}
    />
  )
}