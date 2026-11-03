import type { UserOut } from '../api/types'

// Hanya untuk menyembunyikan aksi di UI. Penegakan sebenarnya ada di backend (403).

type Actor = Pick<UserOut, 'role' | 'can_send_misp' | 'is_active'> | null

export function canCheck(user: Actor): boolean {
  if (user === null || !user.is_active) return false
  return user.role === 'admin' || user.role === 'analyst'
}

export function canSendMisp(user: Actor): boolean {
  if (user === null || !user.is_active) return false
  if (user.role === 'admin') return true
  return user.role === 'analyst' && user.can_send_misp
}

// Teks pengganti form MISP untuk akun yang tidak boleh mengirim; null bila boleh.
export function mispDeniedText(user: Actor): string | null {
  if (canSendMisp(user)) return null
  if (user !== null && user.role === 'analyst') return 'Kirim ke MISP butuh izin dari admin.'
  return 'Akun ini hanya dapat melihat; tidak dapat mengirim ke MISP.'
}
