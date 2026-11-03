import type { CheckOut, IocOut, IocStatus } from '../api/types'

// Aturan tampilan dan validasi pengiriman MISP. Fungsi murni; tidak ada akses jaringan atau DOM.

// ---------- Status submission ----------

export interface IocStatusView {
  label: string
  // 'gagal' = chip berbingkai merah + ikon X (pengecualian Keputusan 10). Selain itu netral: tanpa hijau,
  // tanpa kuning (kuning milik verdict PERLU_PEMERIKSAAN), tanpa warna verdict.
  tone: 'netral' | 'gagal'
  // Ikon centang hanya untuk `sent` (benar-benar sampai ke MISP).
  confirmed: boolean
  // Hanya `failed` yang boleh dikirim ulang; `pending` selalu 409 di backend.
  retryable: boolean
}

const STATUS_VIEWS: Record<IocStatus, IocStatusView> = {
  pending: { label: 'Sedang diproses (pending)', tone: 'netral', confirmed: false, retryable: false },
  mock_sent: { label: 'Terkirim (mock)', tone: 'netral', confirmed: false, retryable: false },
  sent: { label: 'Terkirim ke MISP', tone: 'netral', confirmed: true, retryable: false },
  failed: { label: 'Gagal', tone: 'gagal', confirmed: false, retryable: true },
}

// `mock_sent` tidak pernah berlabel "Terkirim ke MISP": itu hasil mock, bukan MISP sungguhan (Aturan tampilan 5).
export function iocStatusView(status: IocStatus): IocStatusView {
  return STATUS_VIEWS[status]
}

export const PENDING_HINT = 'Bila tertahan lama, hubungi admin.'

// ---------- Pencocokan submission ----------

// Daftar dari server urut terbaru dulu; satu check punya paling banyak satu submission (UNIQUE(check_id)).
export function findSubmissionForCheck(
  items: readonly IocOut[],
  checkId: number,
): IocOut | null {
  return items.find((item) => item.check_id === checkId) ?? null
}

// IP yang sama sudah dikirim lewat check LAIN. `failed` tidak dihitung: kiriman gagal tidak pernah sampai ke
// MISP, jadi kata "sudah pernah dikirim" akan salah. Yang terbaru dipilih (daftar urut terbaru dulu).
export function findSameIpElsewhere(
  items: readonly IocOut[],
  check: Pick<CheckOut, 'id' | 'ip'>,
): IocOut | null {
  return (
    items.find(
      (item) =>
        item.ip === check.ip &&
        item.check_id !== check.id &&
        item.status !== 'failed',
    ) ?? null
  )
}

// Check baru atas IP yang sama adalah operasi baru, bukan retry, jadi kata "duplikat" sengaja tidak dipakai
// (Keputusan 14; riset §7: lookup ulang bukan sighting otomatis).
export function confirmText(previous: Pick<IocOut, 'check_id' | 'status'>): string {
  return `IP ini sudah pernah dikirim lewat check #${previous.check_id} (${previous.status}). Kirim lagi sebagai catatan baru?`
}

// ---------- Validasi form ----------

export const REASON_MIN = 10
export const REASON_MAX = 2000
export const TAGS_MAX = 20
export const TAG_MAX_LENGTH = 64

// Backend (Pydantic) menghitung code point Unicode, sedangkan String.length menghitung unit UTF-16:
// lima emoji = 10 unit tetapi 5 karakter di server.
export function countChars(text: string): number {
  return Array.from(text).length
}

// Dipisah koma, dipangkas, entri kosong dibuang ("a,,b" atau koma di ujung tidak boleh mengirim "" yang
// ditolak backend dengan min_length=1).
export function parseTags(text: string): string[] {
  return text
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag !== '')
}

export type SubmissionValidation =
  | { ok: true; reason: string; tags: string[] }
  | { ok: false; reasonError: string | null; tagsError: string | null }

function clip(text: string): string {
  const chars = Array.from(text)
  return chars.length > 20 ? `${chars.slice(0, 20).join('')}…` : text
}

// Backend memangkas spasi sebelum memeriksa 10-2000, jadi yang dihitung dan dikirim adalah hasil pangkas.
export function validateSubmission(
  reasonInput: string,
  tagsInput: string,
): SubmissionValidation {
  const reason = reasonInput.trim()
  const tags = parseTags(tagsInput)
  const length = countChars(reason)

  let reasonError: string | null = null
  if (length < REASON_MIN) {
    reasonError = `Alasan minimal ${REASON_MIN} karakter (sekarang ${length}).`
  } else if (length > REASON_MAX) {
    reasonError = `Alasan maksimal ${REASON_MAX} karakter (sekarang ${length}).`
  }

  let tagsError: string | null = null
  if (tags.length > TAGS_MAX) {
    tagsError = `Maksimal ${TAGS_MAX} tag (sekarang ${tags.length}).`
  } else {
    const tooLong = tags.find((tag) => countChars(tag) > TAG_MAX_LENGTH)
    if (tooLong !== undefined) {
      tagsError = `Tag "${clip(tooLong)}" lebih dari ${TAG_MAX_LENGTH} karakter.`
    }
  }

  if (reasonError !== null || tagsError !== null) {
    return { ok: false, reasonError, tagsError }
  }
  return { ok: true, reason, tags }
}

// ---------- Daftar submission di memori ----------

// Penyegaran halaman terdepan: baris yang sudah dikenal diperbarui di tempat (status bisa berubah, mis.
// failed → mock_sent), baris baru dari orang lain diletakkan di atas dengan urutan server.
export function applyHead(
  existing: readonly IocOut[],
  incoming: readonly IocOut[],
): IocOut[] {
  const byId = new Map(incoming.map((item) => [item.id, item]))
  const known = new Set(existing.map((item) => item.id))
  const newcomers = incoming.filter((item) => !known.has(item.id))
  return [...newcomers, ...existing.map((item) => byId.get(item.id) ?? item)]
}

// Halaman berikutnya ditambahkan di belakang dengan dedup per `id` (offset bisa bergeser karena kiriman baru).
export function appendPage(
  existing: readonly IocOut[],
  incoming: readonly IocOut[],
): IocOut[] {
  const seen = new Set(existing.map((item) => item.id))
  const merged = [...existing]
  for (const item of incoming) {
    if (seen.has(item.id)) continue
    seen.add(item.id)
    merged.push(item)
  }
  return merged
}

// Hasil POST: ganti baris yang sama (kirim ulang memakai baris yang sama) atau taruh di paling atas.
export function upsertSubmission(
  existing: readonly IocOut[],
  item: IocOut,
): IocOut[] {
  if (existing.some((candidate) => candidate.id === item.id)) {
    return existing.map((candidate) => (candidate.id === item.id ? item : candidate))
  }
  return [item, ...existing]
}
