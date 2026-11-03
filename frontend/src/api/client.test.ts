import { describe, expect, it, vi } from 'vitest'
import { createApiClient, isUnreachable, type ApiFailure } from './client'

type FetchCall = { url: string; init: RequestInit }

function setup(
  respond: (call: FetchCall) => Response | Promise<Response>,
  initialToken: string | null = 'token-A',
) {
  const state = { token: initialToken }
  const calls: FetchCall[] = []
  const onUnauthorized = vi.fn()
  const fetchImpl = ((url: string, init: RequestInit) => {
    const call = { url, init }
    calls.push(call)
    return Promise.resolve(respond(call))
  }) as unknown as typeof fetch
  const client = createApiClient({
    getToken: () => state.token,
    onUnauthorized,
    fetchImpl,
  })
  return { client, calls, state, onUnauthorized }
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('createApiClient', () => {
  it('mengirim Bearer dari getToken() dan memakai prefix /api/v1', async () => {
    const { client, calls } = setup(() => json(200, { ok: 1 }))
    const result = await client.get('/auth/me')
    expect(result).toEqual({ ok: true, status: 200, data: { ok: 1 } })
    expect(calls[0].url).toBe('/api/v1/auth/me')
    expect(new Headers(calls[0].init.headers).get('Authorization')).toBe(
      'Bearer token-A',
    )
    expect(calls[0].init.credentials).toBe('omit')
  })

  it('auth:false tidak mengirim Authorization (login, health)', async () => {
    const { client, calls } = setup(() => json(200, {}))
    await client.get('/health', { auth: false })
    expect(new Headers(calls[0].init.headers).has('Authorization')).toBe(false)
  })

  it('form dikirim sebagai URLSearchParams (bukan JSON)', async () => {
    const { client, calls } = setup(() => json(200, { access_token: 'x' }))
    const form = new URLSearchParams({ username: 'u', password: 'p' })
    await client.post('/auth/login', { form, auth: false, handleUnauthorized: false })
    expect(calls[0].init.body).toBeInstanceOf(URLSearchParams)
    expect(new Headers(calls[0].init.headers).has('Content-Type')).toBe(false)
  })

  it('401 pada request ber-token memanggil onUnauthorized sekali', async () => {
    const { client, onUnauthorized } = setup(() => json(401, { detail: 'x' }))
    const result = await client.get('/checks')
    expect(result).toMatchObject({ ok: false, status: 401, kind: 'http' })
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('401 login (tanpa token) TIDAK memicu logout global', async () => {
    const { client, onUnauthorized } = setup(
      () => json(401, { detail: 'Username atau password salah' }),
      null,
    )
    const result = await client.post('/auth/login', {
      form: new URLSearchParams(),
      auth: false,
      handleUnauthorized: false,
    })
    expect(result).toMatchObject({ ok: false, status: 401 })
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('handleUnauthorized:false menahan logout global walau request ber-token (GET /auth/me tepat setelah login)', async () => {
    // Token sudah terpasang (hasil login) dan masih berlaku, jadi hanya flag ini yang mencegah logout global;
    // AuthProvider menangani kegagalan itu sendiri (token dibuang, pesan login ditampilkan).
    const { client, onUnauthorized } = setup(() => json(401, { detail: 'x' }))
    const result = await client.get('/auth/me', { handleUnauthorized: false })
    expect(result).toMatchObject({ ok: false, status: 401, kind: 'http' })
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('401 basi: token sudah berganti saat request berjalan, jadi diabaikan', async () => {
    const { client, state, onUnauthorized } = setup(() => {
      state.token = 'token-B' // login ulang terjadi sebelum respons tiba
      return json(401, { detail: 'x' })
    })
    await client.get('/checks')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('401 setelah logout (token null) juga diabaikan', async () => {
    const { client, state, onUnauthorized } = setup(() => {
      state.token = null
      return json(401, { detail: 'x' })
    })
    await client.get('/checks')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('kegagalan jaringan menjadi kind network, bukan lemparan galat', async () => {
    const client = createApiClient({
      getToken: () => 'token-A',
      onUnauthorized: vi.fn(),
      fetchImpl: (() => Promise.reject(new TypeError('Failed to fetch'))) as typeof fetch,
    })
    expect(await client.get('/health', { auth: false })).toEqual({
      ok: false,
      status: 0,
      kind: 'network',
      body: null,
    })
  })

  it('200 bukan JSON = invalid; 5xx bukan JSON = http dengan body null', async () => {
    const ok = setup(() => new Response('<html>', { status: 200 }))
    expect(await ok.client.get('/health', { auth: false })).toMatchObject({
      ok: false,
      kind: 'invalid',
    })
    const bad = setup(() => new Response('Bad Gateway', { status: 502 }))
    expect(await bad.client.get('/health', { auth: false })).toEqual({
      ok: false,
      status: 502,
      kind: 'http',
      body: null,
    })
  })

  it('503 membawa badan JSON (dibutuhkan untuk /health degraded)', async () => {
    const { client } = setup(() => json(503, { status: 'degraded', db: 'error' }))
    expect(await client.get('/health', { auth: false })).toMatchObject({
      ok: false,
      status: 503,
      body: { db: 'error' },
    })
  })

  it('abortAll() membatalkan request berjalan dan hasilnya kind aborted', async () => {
    const client = createApiClient({
      getToken: () => 'token-A',
      onUnauthorized: vi.fn(),
      fetchImpl: ((_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          )
        })) as unknown as typeof fetch,
    })
    const pending = client.get('/checks')
    client.abortAll()
    expect(await pending).toMatchObject({ ok: false, kind: 'aborted' })
  })
})

describe('isUnreachable', () => {
  const failure = (over: Partial<ApiFailure>): ApiFailure => ({
    ok: false,
    status: 0,
    kind: 'http',
    body: null,
    ...over,
  })

  it('jaringan gagal dan 502/503/504 tanpa badan (proxy Vite saat backend mati) = tidak terjangkau', () => {
    expect(isUnreachable(failure({ kind: 'network' }))).toBe(true)
    for (const status of [502, 503, 504]) {
      expect(isUnreachable(failure({ status }))).toBe(true)
    }
  })

  it('502 dan 503 DENGAN badan JSON bukan "tidak terjangkau" (IocOut gagal MISP, HealthResponse)', () => {
    expect(isUnreachable(failure({ status: 502, body: { status: 'failed' } }))).toBe(false)
    expect(isUnreachable(failure({ status: 503, body: { db: 'error' } }))).toBe(false)
  })

  it('500 tanpa badan tetap galat server; 401/404 dan aborted bukan tidak terjangkau', () => {
    expect(isUnreachable(failure({ status: 500 }))).toBe(false)
    expect(isUnreachable(failure({ status: 401 }))).toBe(false)
    expect(isUnreachable(failure({ status: 404 }))).toBe(false)
    expect(isUnreachable(failure({ kind: 'aborted' }))).toBe(false)
  })
})
