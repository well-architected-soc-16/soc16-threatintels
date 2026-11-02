// Klien HTTP tipis di atas fetch. Token dibaca lewat getToken() (disimpan di memori oleh pemanggil);
// modul ini tidak menyimpan token, tidak mencetak apa pun ke console, dan tidak pernah membuat URL berisi token.

const BASE = '/api/v1'

export type ApiFailureKind = 'http' | 'network' | 'invalid' | 'aborted'

export interface ApiFailure {
  ok: false
  status: number
  kind: ApiFailureKind
  body: unknown
}

export type ApiResult<T> = { ok: true; status: number; data: T } | ApiFailure

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH'
  json?: unknown
  form?: URLSearchParams
  // Kirim header Authorization. false untuk login dan /health.
  auth?: boolean
  // 401 memicu logout global. false untuk login dan pemanggilan yang menangani 401 sendiri.
  handleUnauthorized?: boolean
}

export interface ApiClientDeps {
  getToken: () => string | null
  onUnauthorized: () => void
  fetchImpl?: typeof fetch
}

export interface ApiClient {
  get: <T>(path: string, options?: RequestOptions) => Promise<ApiResult<T>>
  post: <T>(path: string, options?: RequestOptions) => Promise<ApiResult<T>>
  // Batalkan semua request yang masih berjalan (dipanggil saat logout).
  abortAll: () => void
}

export function createApiClient(deps: ApiClientDeps): ApiClient {
  const inFlight = new Set<AbortController>()

  async function request<T>(
    path: string,
    options: RequestOptions,
  ): Promise<ApiResult<T>> {
    const {
      method = 'GET',
      json,
      form,
      auth = true,
      handleUnauthorized = true,
    } = options
    const doFetch = deps.fetchImpl ?? fetch
    const tokenAtSend = auth ? deps.getToken() : null

    const headers = new Headers({ Accept: 'application/json' })
    if (tokenAtSend) headers.set('Authorization', `Bearer ${tokenAtSend}`)
    let body: BodyInit | undefined
    if (form) {
      // Content-Type form-urlencoded diisi otomatis oleh fetch untuk URLSearchParams.
      body = form
    } else if (json !== undefined) {
      headers.set('Content-Type', 'application/json')
      body = JSON.stringify(json)
    }

    const controller = new AbortController()
    inFlight.add(controller)
    const failure = (kind: ApiFailureKind): ApiFailure => ({
      ok: false,
      status: 0,
      kind: controller.signal.aborted ? 'aborted' : kind,
      body: null,
    })

    let text: string
    let response: Response
    try {
      response = await doFetch(`${BASE}${path}`, {
        method,
        headers,
        body,
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
      })
      text = await response.text()
    } catch {
      inFlight.delete(controller)
      return failure('network')
    }
    inFlight.delete(controller)

    let parsed: unknown = null
    let parseOk = true
    if (text !== '') {
      try {
        parsed = JSON.parse(text)
      } catch {
        parseOk = false
      }
    }

    // 401 dari request yang dikirim dengan token yang MASIH berlaku saja yang mengeluarkan user.
    // Respons lama dari sesi sebelumnya (logout atau login ulang saat request berjalan) diabaikan.
    if (
      response.status === 401 &&
      handleUnauthorized &&
      tokenAtSend !== null &&
      deps.getToken() === tokenAtSend
    ) {
      deps.onUnauthorized()
    }

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        kind: 'http',
        body: parseOk ? parsed : null,
      }
    }
    if (!parseOk || text === '') {
      return { ok: false, status: response.status, kind: 'invalid', body: null }
    }
    return { ok: true, status: response.status, data: parsed as T }
  }

  return {
    get: (path, options = {}) => request(path, { ...options, method: 'GET' }),
    post: (path, options = {}) => request(path, { ...options, method: 'POST' }),
    abortAll: () => {
      for (const controller of inFlight) controller.abort()
      inFlight.clear()
    },
  }
}
