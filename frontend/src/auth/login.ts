import type { ApiClient } from '../api/client'
import type { Token, UserOut } from '../api/types'
import type { LoginError } from './AuthContext'
import type { TokenStore } from './tokenStore'

export type LoginOutcome =
  | { ok: true; user: UserOut; token: string }
  | { ok: false; error: LoginError }

// Alur login: POST form-urlencoded lalu GET /auth/me. Dipisah dari komponen agar bisa diuji tanpa DOM.
// Invarian: setelah kegagalan di langkah mana pun, `store` kosong (tidak ada keadaan setengah login).
export async function performLogin(
  api: ApiClient,
  store: TokenStore,
  username: string,
  password: string,
): Promise<LoginOutcome> {
  // Isian dikirim sebagai badan form (bukan query string), jadi tidak pernah masuk URL.
  const form = new URLSearchParams({ username, password })
  // 401 login = salah username/password, bukan sesi berakhir: tidak memicu logout global.
  const response = await api.post<Token>('/auth/login', {
    form,
    auth: false,
    handleUnauthorized: false,
  })
  if (!response.ok) {
    if (response.kind === 'network' || response.kind === 'aborted') {
      return { ok: false, error: 'network' }
    }
    return {
      ok: false,
      error: response.status === 401 ? 'bad_credentials' : 'unexpected',
    }
  }
  const token = response.data.access_token
  if (typeof token !== 'string' || token === '') {
    return { ok: false, error: 'unexpected' }
  }

  store.set(token)
  const me = await api.get<UserOut>('/auth/me', { handleUnauthorized: false })
  if (!me.ok) {
    store.clear()
    return {
      ok: false,
      error:
        me.kind === 'network' || me.kind === 'aborted'
          ? 'network'
          : 'unexpected',
    }
  }
  return { ok: true, user: me.data, token }
}
