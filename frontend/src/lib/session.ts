// Payload JWT hanya dibaca untuk menampilkan jam berakhir sesi. Tanda tangan TIDAK diverifikasi di sini
// (itu tugas backend); hasilnya tidak dipakai untuk keputusan keamanan dan tidak pernah dicetak.

function base64UrlToBytes(input: string): Uint8Array | null {
  try {
    const base64 = input.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const binary = atob(padded)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    return bytes
  } catch {
    return null
  }
}

export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split('.')
  if (parts.length !== 3) return null
  const bytes = base64UrlToBytes(parts[1])
  if (bytes === null) return null
  try {
    const value: unknown = JSON.parse(new TextDecoder().decode(bytes))
    return typeof value === 'object' && value !== null && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : null
  } catch {
    return null
  }
}

// `exp` dalam detik epoch; null bila tidak ada atau bukan angka hingga.
export function getTokenExp(token: string): number | null {
  const exp = decodeJwtPayload(token)?.exp
  return typeof exp === 'number' && Number.isFinite(exp) ? exp : null
}

const jamFormat = new Intl.DateTimeFormat('id-ID', {
  timeZone: 'Asia/Jakarta',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

// "14:33" (WIB). Locale id-ID memisahkan jam dengan titik ("14.33"); bagian-bagiannya dirakit ulang dengan
// ":" tetap agar hasilnya sama di semua peramban. Satu-satunya konversi zona waktu di frontend (Keputusan 22).
export function formatSessionEnd(expSeconds: number): string {
  const parts = jamFormat.formatToParts(new Date(expSeconds * 1000))
  const hour = parts.find((p) => p.type === 'hour')?.value ?? '--'
  const minute = parts.find((p) => p.type === 'minute')?.value ?? '--'
  return `${hour}:${minute}`
}
