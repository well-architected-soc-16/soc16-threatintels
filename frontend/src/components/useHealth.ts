import { useEffect, useState } from 'react'
import type { ApiClient } from '../api/client'
import type { HealthResponse } from '../api/types'
import { parseHealth, type HealthState } from '../lib/health'

const REFRESH_MS = 30_000

// null = belum ada hasil. /health publik: tanpa Authorization dan tanpa efek 401 global.
// Diulang berkala agar badge tidak menampilkan "sehat" untuk backend yang sudah mati.
export function useHealth(api: ApiClient, refreshKey: unknown): HealthState | null {
  const [state, setState] = useState<HealthState | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const result = await api.get<HealthResponse>('/health', {
        auth: false,
        handleUnauthorized: false,
      })
      if (cancelled || (!result.ok && result.kind === 'aborted')) return
      setState(parseHealth(result))
    }
    void load()
    const timer = setInterval(() => void load(), REFRESH_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [api, refreshKey])

  return state
}
