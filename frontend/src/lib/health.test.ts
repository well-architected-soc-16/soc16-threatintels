import { describe, expect, it } from 'vitest'
import type { ApiResult } from '../api/client'
import { parseHealth } from './health'

const body = (over: Record<string, unknown> = {}) => ({
  status: 'ok',
  db: 'ok',
  misp_mode: 'mock',
  time: '2026-11-02T14:00:00+07:00',
  ...over,
})

describe('parseHealth', () => {
  it('200 sehat membawa misp_mode', () => {
    const result: ApiResult<unknown> = { ok: true, status: 200, data: body() }
    expect(parseHealth(result)).toEqual({ kind: 'ok', mispMode: 'mock' })
    expect(
      parseHealth({ ok: true, status: 200, data: body({ misp_mode: 'live' }) }),
    ).toEqual({ kind: 'ok', mispMode: 'live' })
  })

  it('503 dengan badan HealthResponse = degraded (API: DB error)', () => {
    const result: ApiResult<unknown> = {
      ok: false,
      status: 503,
      kind: 'http',
      body: body({ status: 'degraded', db: 'error' }),
    }
    expect(parseHealth(result)).toEqual({ kind: 'degraded', mispMode: 'mock' })
  })

  it('backend mati, proxy gagal, atau badan bukan HealthResponse = unreachable', () => {
    expect(
      parseHealth({ ok: false, status: 0, kind: 'network', body: null }),
    ).toEqual({ kind: 'unreachable' })
    expect(
      parseHealth({ ok: false, status: 500, kind: 'http', body: null }),
    ).toEqual({ kind: 'unreachable' })
    expect(
      parseHealth({ ok: false, status: 502, kind: 'http', body: body() }),
    ).toEqual({ kind: 'unreachable' })
    expect(
      parseHealth({ ok: true, status: 200, data: { status: 'ok' } }),
    ).toEqual({ kind: 'unreachable' })
    expect(parseHealth({ ok: true, status: 200, data: null })).toEqual({
      kind: 'unreachable',
    })
  })
})
