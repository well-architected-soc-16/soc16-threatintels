import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { createApiClient } from '../api/client'
import type { UserOut } from '../api/types'
import { formatSessionEnd, getTokenExp } from '../lib/session'
import { AuthContext, type AuthContextValue, type LoginResult } from './AuthContext'
import { performLogin } from './login'
import { TokenStore } from './tokenStore'

export const SESSION_EXPIRED_NOTICE = 'Sesi berakhir, login lagi'

interface Session {
  user: UserOut
  exp: number | null
}

// Token hanya hidup di memori (TokenStore): tidak ditulis ke penyimpanan peramban mana pun dan tidak ada
// cookie buatan JS (Keputusan 3). Refresh halaman berarti login ulang.
export function AuthProvider({ children }: { children: ReactNode }) {
  // Stabil sepanjang umur provider; hanya dipakai di dalam callback (login, logout, getToken), tidak saat render.
  const [store] = useState(() => new TokenStore())
  const [session, setSession] = useState<Session | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [{ api, endSession }] = useState(() => {
    // Satu jalur keluar untuk logout manual dan 401: batalkan request berjalan agar respons terlambat
    // tidak mengisi ulang state, lalu hapus token dan user.
    const endSession = (reason: string | null) => {
      api.abortAll()
      store.clear()
      setSession(null)
      setNotice(reason)
    }
    const api = createApiClient({
      getToken: () => store.get(),
      onUnauthorized: () => endSession(SESSION_EXPIRED_NOTICE),
    })
    return { api, endSession }
  })

  const login = useCallback(
    async (username: string, password: string): Promise<LoginResult> => {
      const outcome = await performLogin(api, store, username, password)
      if (!outcome.ok) return outcome
      setNotice(null)
      setSession({ user: outcome.user, exp: getTokenExp(outcome.token) })
      return { ok: true }
    },
    [api, store],
  )

  const logout = useCallback(() => endSession(null), [endSession])

  const refreshUser = useCallback(async () => {
    const me = await api.get<UserOut>('/auth/me')
    if (me.ok) {
      setSession((current) =>
        current === null ? current : { ...current, user: me.data },
      )
    }
  }, [api])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      sessionEnd:
        session?.exp != null ? formatSessionEnd(session.exp) : null,
      notice,
      api,
      login,
      logout,
      refreshUser,
    }),
    [session, notice, api, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
