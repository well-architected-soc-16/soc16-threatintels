import { createContext } from 'react'
import type { ApiClient } from '../api/client'
import type { UserOut } from '../api/types'

export type LoginError = 'bad_credentials' | 'network' | 'unexpected'
export type LoginResult = { ok: true } | { ok: false; error: LoginError }

export interface AuthContextValue {
  user: UserOut | null
  // Jam berakhir sesi dalam WIB ("14:33"), dari klaim exp; null bila tidak terbaca.
  sessionEnd: string | null
  // Pesan di halaman login (mis. "Sesi berakhir, login lagi"); null bila tidak ada.
  notice: string | null
  api: ApiClient
  login: (username: string, password: string) => Promise<LoginResult>
  logout: () => void
  // Validasi ulang sesi lewat GET /auth/me (401 otomatis mengembalikan ke login).
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
