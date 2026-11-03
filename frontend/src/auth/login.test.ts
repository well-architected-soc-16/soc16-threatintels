import { describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../api/client'
import type { UserOut } from '../api/types'
import { performLogin } from './login'
import { TokenStore } from './tokenStore'

const user: UserOut = {
  id: 2,
  username: 'analyst',
  role: 'analyst',
  can_send_misp: false,
  is_active: true,
  created_at: '2026-11-02T10:00:00+07:00',
  updated_at: '2026-11-02T10:00:00+07:00',
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>

function setup(handler: Handler) {
  const store = new TokenStore()
  const onUnauthorized = vi.fn()
  const calls: { url: string; init: RequestInit }[] = []
  const api = createApiClient({
    getToken: () => store.get(),
    onUnauthorized,
    fetchImpl: ((url: string, init: RequestInit) => {
      calls.push({ url, init })
      return Promise.resolve(handler(url, init))
    }) as unknown as typeof fetch,
  })
  return { api, store, onUnauthorized, calls }
}

describe('performLogin', () => {
  it('berhasil: token tersimpan, /auth/me dipanggil dengan Bearer, user dikembalikan', async () => {
    const { api, store, calls } = setup((url) =>
      url.endsWith('/auth/login')
        ? json(200, { access_token: 'tok-1', token_type: 'bearer' })
        : json(200, user),
    )
    const outcome = await performLogin(api, store, 'analyst', 'rahasia-uji')
    expect(outcome).toEqual({ ok: true, user, token: 'tok-1' })
    expect(store.get()).toBe('tok-1')
    expect(new Headers(calls[1].init.headers).get('Authorization')).toBe(
      'Bearer tok-1',
    )
  })

  it('isian dikirim sebagai badan form, tidak pernah di URL', async () => {
    const { api, store, calls } = setup(() => json(401, { detail: 'x' }))
    await performLogin(api, store, 'analyst', 'rahasia-uji')
    expect(calls[0].url).toBe('/api/v1/auth/login')
    expect(calls[0].url).not.toContain('rahasia-uji')
    expect(calls[0].init.body).toBeInstanceOf(URLSearchParams)
    expect((calls[0].init.body as URLSearchParams).get('password')).toBe(
      'rahasia-uji',
    )
  })

  it('401 login = bad_credentials, token kosong, /auth/me tidak dipanggil, tanpa logout global', async () => {
    const { api, store, calls, onUnauthorized } = setup(() =>
      json(401, { detail: 'Username atau password salah' }),
    )
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'bad_credentials',
    })
    expect(store.get()).toBeNull()
    expect(calls).toHaveLength(1)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('backend tidak terjangkau = network', async () => {
    const store = new TokenStore()
    const api = createApiClient({
      getToken: () => store.get(),
      onUnauthorized: vi.fn(),
      fetchImpl: (() => Promise.reject(new TypeError('offline'))) as typeof fetch,
    })
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'network',
    })
    expect(store.get()).toBeNull()
  })

  it('login sukses tetapi /auth/me 401: token dibuang, bukan setengah login, tanpa logout global', async () => {
    const { api, store, onUnauthorized } = setup((url) =>
      url.endsWith('/auth/login')
        ? json(200, { access_token: 'tok-1', token_type: 'bearer' })
        : json(401, { detail: 'Not authenticated' }),
    )
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'unexpected',
    })
    expect(store.get()).toBeNull()
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('login sukses tetapi /auth/me gagal jaringan: token dibuang, galat network', async () => {
    let call = 0
    const store = new TokenStore()
    const api = createApiClient({
      getToken: () => store.get(),
      onUnauthorized: vi.fn(),
      fetchImpl: (() =>
        ++call === 1
          ? Promise.resolve(json(200, { access_token: 'tok-1', token_type: 'bearer' }))
          : Promise.reject(new TypeError('offline'))) as typeof fetch,
    })
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'network',
    })
    expect(store.get()).toBeNull()
  })

  it('backend mati di balik proxy Vite (502 text/plain, badan kosong) = network, bukan "unexpected"', async () => {
    const { api, store, onUnauthorized } = setup(
      () => new Response('', { status: 502, headers: { 'Content-Type': 'text/plain' } }),
    )
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'network',
    })
    expect(store.get()).toBeNull()
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('login sukses tetapi /auth/me 502 (backend mati di tengah): token dibuang, galat network', async () => {
    const { api, store } = setup((url) =>
      url.endsWith('/auth/login')
        ? json(200, { access_token: 'tok-1', token_type: 'bearer' })
        : new Response('', { status: 502 }),
    )
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'network',
    })
    expect(store.get()).toBeNull()
  })

  it('500 tanpa badan tetap "unexpected" (galat server, bukan tidak terjangkau)', async () => {
    const { api, store } = setup(() => new Response('Internal Server Error', { status: 500 }))
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'unexpected',
    })
  })

  it.each([
    ['token kosong', { access_token: '', token_type: 'bearer' }],
    ['tanpa access_token', { token_type: 'bearer' }],
  ])('respons login %s = unexpected, token kosong', async (_name, body) => {
    const { api, store } = setup(() => json(200, body))
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'unexpected',
    })
    expect(store.get()).toBeNull()
  })

  it('422 dari login (bentuk di luar dugaan) = unexpected', async () => {
    const { api, store } = setup(() =>
      json(422, { detail: [{ loc: ['body', 'password'], msg: 'Field required' }] }),
    )
    expect(await performLogin(api, store, 'x', 'y')).toEqual({
      ok: false,
      error: 'unexpected',
    })
  })
})

describe('TokenStore', () => {
  it('menyimpan dan menghapus token; tidak ikut ter-enumerasi atau ter-serialisasi', () => {
    const store = new TokenStore()
    store.set('rahasia-token')
    expect(store.get()).toBe('rahasia-token')
    expect(JSON.stringify(store)).toBe('{}')
    expect(Object.keys(store)).toEqual([])
    store.clear()
    expect(store.get()).toBeNull()
  })
})
