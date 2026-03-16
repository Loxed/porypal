import { useState, useCallback } from 'react'

export function useFetch() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = useCallback(async (fn) => {
    setLoading(true)
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError(e.message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, run }
}