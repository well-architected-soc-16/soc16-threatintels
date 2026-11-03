import type { CheckOut, CheckPage } from './types'

// Penjaga bentuk untuk balasan 2xx. Komponen mengandalkan `sources`/`flags` berupa array dan
// `evidence_summary` berupa objek; balasan JSON lain yang lolos (gateway, proxy, versi backend berbeda)
// harus ditolak di tepi, bukan membuat tampilan crash.

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function isSourceResult(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.source === 'string' &&
    typeof value.status === 'string' &&
    isRecord(value.evidence_summary) &&
    isStringArray(value.flags)
  )
}

export function isCheckOut(value: unknown): value is CheckOut {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    typeof value.ip === 'string' &&
    typeof value.assessment_status === 'string' &&
    (value.risk_score === null || typeof value.risk_score === 'number') &&
    (value.indication === null || typeof value.indication === 'string') &&
    typeof value.coverage === 'string' &&
    typeof value.scoring_version === 'string' &&
    typeof value.checked_by === 'string' &&
    typeof value.checked_at === 'string' &&
    isStringArray(value.flags) &&
    Array.isArray(value.sources) &&
    value.sources.every(isSourceResult)
  )
}

export function isCheckPage(value: unknown): value is CheckPage {
  return (
    isRecord(value) &&
    typeof value.total === 'number' &&
    Number.isFinite(value.total) &&
    Array.isArray(value.items) &&
    value.items.every(isCheckOut)
  )
}
