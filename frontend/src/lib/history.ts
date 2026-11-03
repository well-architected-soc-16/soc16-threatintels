import type { CheckOut } from '../api/types'

// Riwayat diurutkan terbaru di atas. Semua fungsi mengembalikan array baru (tidak mengubah masukan).

// Menambahkan halaman berikutnya di belakang riwayat, dengan dedup per `id`: check baru (milik kita atau
// orang lain) menggeser offset, sehingga halaman berikutnya bisa memuat baris yang sudah ada.
export function mergeHistory(
  existing: readonly CheckOut[],
  incoming: readonly CheckOut[],
): CheckOut[] {
  const seen = new Set(existing.map((check) => check.id))
  const merged = [...existing]
  for (const check of incoming) {
    if (seen.has(check.id)) continue
    seen.add(check.id)
    merged.push(check)
  }
  return merged
}

// Check baru masuk paling atas. Dedup per id, bukan per IP: "Cek ulang" atas IP yang sama membuat baris baru.
export function prependCheck(
  history: readonly CheckOut[],
  check: CheckOut,
): CheckOut[] {
  return [check, ...history.filter((item) => item.id !== check.id)]
}

// Penyaringan client-side atas yang sudah dimuat (bukan pencarian penuh; backend tanpa parameter filter).
export function filterHistory(
  history: readonly CheckOut[],
  query: string,
): CheckOut[] {
  const needle = query.trim().toLowerCase()
  if (needle === '') return [...history]
  return history.filter((check) => check.ip.toLowerCase().includes(needle))
}

export function hasMore(loaded: number, total: number | null): boolean {
  return total !== null && loaded < total
}
