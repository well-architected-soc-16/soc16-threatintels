import type { ApiResult } from '../api/client'
import type { HealthResponse } from '../api/types'

export type HealthState =
  | { kind: 'ok'; mispMode: HealthResponse['misp_mode'] }
  // 503: API hidup tetapi database bermasalah (badan respons tetap HealthResponse).
  | { kind: 'degraded'; mispMode: HealthResponse['misp_mode'] }
  // Backend mati, proxy gagal, atau badan respons bukan HealthResponse.
  | { kind: 'unreachable' }

function asHealth(body: unknown): HealthResponse | null {
  if (typeof body !== 'object' || body === null) return null
  const b = body as Record<string, unknown>
  const mode = b.misp_mode
  if (mode !== 'mock' && mode !== 'live') return null
  if (b.db !== 'ok' && b.db !== 'error') return null
  if (b.status !== 'ok' && b.status !== 'degraded') return null
  return body as HealthResponse
}

export function parseHealth(result: ApiResult<unknown>): HealthState {
  const body = result.ok ? result.data : result.body
  const health = asHealth(body)
  if (health === null) return { kind: 'unreachable' }
  if (result.ok && health.status === 'ok' && health.db === 'ok') {
    return { kind: 'ok', mispMode: health.misp_mode }
  }
  if (!result.ok && result.status !== 503) return { kind: 'unreachable' }
  return { kind: 'degraded', mispMode: health.misp_mode }
}
