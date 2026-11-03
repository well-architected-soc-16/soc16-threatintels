import { isUnreachable, type ApiFailure } from '../api/client'
import type {
  CheckRejected,
  IocDuplicate,
  IocOut,
  RejectReasonCode,
} from '../api/types'

// Parser murni dari (status, body) ke bentuk galat yang siap ditampilkan. Pesan berasal dari field backend
// yang aman; field `input` dan `ctx` pada galat validasi FastAPI TIDAK PERNAH disalin (422 pada login bisa
// memantulkan isian form, termasuk password).

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isCheckRejected(body: unknown): body is CheckRejected {
  return (
    isRecord(body) &&
    body.assessment_status === 'INPUT_DITOLAK' &&
    typeof body.message === 'string' &&
    typeof body.reason_code === 'string'
  )
}

export function isIocDuplicate(body: unknown): body is IocDuplicate {
  return (
    isRecord(body) &&
    typeof body.detail === 'string' &&
    typeof body.submission_id === 'number'
  )
}

export function isIocOut(body: unknown): body is IocOut {
  return (
    isRecord(body) &&
    typeof body.id === 'number' &&
    typeof body.check_id === 'number' &&
    typeof body.status === 'string' &&
    typeof body.ip === 'string'
  )
}

function detailString(body: unknown): string | null {
  return isRecord(body) && typeof body.detail === 'string' ? body.detail : null
}

// Nama field dari galat validasi FastAPI ({detail:[{loc:[...], msg, input, ...}]}), tanpa nilai input.
function validationFields(body: unknown): string[] | null {
  if (!isRecord(body) || !Array.isArray(body.detail)) return null
  const fields: string[] = []
  for (const item of body.detail) {
    if (!isRecord(item) || !Array.isArray(item.loc)) continue
    const last = item.loc[item.loc.length - 1]
    if (typeof last === 'string' || typeof last === 'number') {
      const name = String(last)
      if (!fields.includes(name)) fields.push(name)
    }
  }
  return fields
}

export function validationMessage(body: unknown): string {
  const fields = validationFields(body)
  if (fields === null) return 'Input tidak valid.'
  return fields.length > 0
    ? `Input tidak valid: ${fields.join(', ')}.`
    : 'Input tidak valid.'
}

export type CheckError =
  | { kind: 'input_ditolak'; message: string; reasonCode: RejectReasonCode }
  | { kind: 'validation'; message: string }
  | { kind: 'unauthorized' }
  | { kind: 'forbidden'; message: string }
  | { kind: 'server'; message: string }
  | { kind: 'network' }
  | { kind: 'unknown'; message: string }

export function parseCheckError(failure: ApiFailure): CheckError {
  if (isUnreachable(failure) || failure.kind === 'aborted') {
    return { kind: 'network' }
  }
  const { status, body } = failure
  if (status === 401) return { kind: 'unauthorized' }
  if (status === 403) {
    return {
      kind: 'forbidden',
      message: detailString(body) ?? 'Akun ini tidak berhak membuat pengecekan.',
    }
  }
  if (status === 422) {
    // Dua bentuk: INPUT_DITOLAK buatan backend, atau galat validasi standar FastAPI.
    if (isCheckRejected(body)) {
      return {
        kind: 'input_ditolak',
        message: body.message,
        reasonCode: body.reason_code,
      }
    }
    return { kind: 'validation', message: validationMessage(body) }
  }
  if (status >= 500 || failure.kind === 'invalid') {
    return {
      kind: 'server',
      message: 'Server tidak dapat memproses permintaan. Coba lagi sebentar lagi.',
    }
  }
  return {
    kind: 'unknown',
    message: detailString(body) ?? `Permintaan gagal (HTTP ${status}).`,
  }
}

export type IocError =
  | { kind: 'not_found'; message: string }
  | { kind: 'duplicate'; message: string; submissionId: number }
  // 422 dengan detail berupa teks: INPUT_DITOLAK atau SUMBER_SIMULASI (tidak ada submission dibuat).
  | { kind: 'rejected'; message: string }
  // 422 galat validasi FastAPI (mis. alasan terlalu pendek).
  | { kind: 'validation'; message: string }
  // 501/502: submission tersimpan sebagai `failed`; badan respons adalah IocOut.
  | { kind: 'failed'; httpStatus: number; submission: IocOut }
  | { kind: 'unauthorized' }
  | { kind: 'forbidden'; message: string }
  | { kind: 'server'; message: string }
  | { kind: 'network' }
  | { kind: 'unknown'; message: string }

export function parseIocError(failure: ApiFailure): IocError {
  if (isUnreachable(failure) || failure.kind === 'aborted') {
    return { kind: 'network' }
  }
  const { status, body } = failure
  if (status === 401) return { kind: 'unauthorized' }
  if (status === 403) {
    return {
      kind: 'forbidden',
      message: 'Akun ini tidak berhak mengirim ke MISP',
    }
  }
  if (status === 404) {
    return {
      kind: 'not_found',
      message: detailString(body) ?? 'Data tidak ditemukan',
    }
  }
  if (status === 409) {
    if (isIocDuplicate(body)) {
      return {
        kind: 'duplicate',
        message: body.detail,
        submissionId: body.submission_id,
      }
    }
    return { kind: 'unknown', message: detailString(body) ?? 'Konflik data.' }
  }
  if (status === 422) {
    const text = detailString(body)
    if (text !== null) return { kind: 'rejected', message: text }
    return { kind: 'validation', message: validationMessage(body) }
  }
  if ((status === 501 || status === 502) && isIocOut(body)) {
    return { kind: 'failed', httpStatus: status, submission: body }
  }
  if (status >= 500 || failure.kind === 'invalid') {
    return {
      kind: 'server',
      message: 'Server tidak dapat memproses permintaan. Coba lagi sebentar lagi.',
    }
  }
  return {
    kind: 'unknown',
    message: detailString(body) ?? `Permintaan gagal (HTTP ${status}).`,
  }
}
