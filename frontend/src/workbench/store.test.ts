import { describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../api/client'
import type { CheckOut, CheckPage } from '../api/types'
import { makeCheck } from '../testing/fixtures'
import {
  createWorkbenchStore,
  MESSAGE_EMPTY_IP,
  MESSAGE_UNREACHABLE,
} from './store'

const check = (id: number, ip = `10.0.0.${id}`): CheckOut => makeCheck({ id, ip })
const page = (items: CheckOut[], total: number, offset = 0): CheckPage => ({
  items,
  total,
  limit: 20,
  offset,
})
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
const empty = (status: number) => new Response('', { status })

interface Call {
  method: string
  url: string
  body: unknown
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

function setup(handler: (call: Call) => Response | Promise<Response>) {
  const calls: Call[] = []
  const onUnauthorized = vi.fn()
  const api = createApiClient({
    getToken: () => 'tok',
    onUnauthorized,
    fetchImpl: ((url: string, init: RequestInit) => {
      const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body
      const call = { method: init.method ?? 'GET', url, body }
      calls.push(call)
      return Promise.resolve(handler(call))
    }) as unknown as typeof fetch,
  })
  return { store: createWorkbenchStore(api), calls, api, onUnauthorized }
}

const ids = (list: CheckOut[]) => list.map((c) => c.id)

describe('loadInitial / loadMore', () => {
  it('memuat halaman pertama (offset 0) dan total', async () => {
    const { store, calls } = setup(() => json(200, page([check(3), check(2), check(1)], 3)))
    await store.loadInitial()
    expect(calls[0].url).toBe('/api/v1/checks?limit=20&offset=0')
    const state = store.getState()
    expect(ids(state.history)).toEqual([3, 2, 1])
    expect(state.total).toBe(3)
    expect(state.historyStatus).toBe('ready')
  })

  it('backend mati (502 kosong): pesan tidak terjangkau, status error', async () => {
    const { store } = setup(() => empty(502))
    await store.loadInitial()
    expect(store.getState().historyStatus).toBe('error')
    expect(store.getState().historyError).toBe(MESSAGE_UNREACHABLE)
  })

  it('loadMore memakai offset = jumlah yang sudah dimuat, dedup per id, dan menyegarkan total', async () => {
    const first = [check(5), check(4), check(3)]
    const { store, calls } = setup(({ url }) =>
      url.endsWith('offset=0')
        ? json(200, page(first, 6))
        : // total bertambah karena ada check baru dari orang lain; baris 3 bergeser masuk lagi
          json(200, page([check(3), check(2), check(1)], 7, 3)),
    )
    await store.loadInitial()
    await store.loadMore()
    expect(calls[1].url).toBe('/api/v1/checks?limit=20&offset=3')
    expect(ids(store.getState().history)).toEqual([5, 4, 3, 2, 1])
    expect(store.getState().total).toBe(7)
  })

  it('"Muat lagi" tidak memanggil server bila semua sudah dimuat', async () => {
    const { store, calls } = setup(() => json(200, page([check(2), check(1)], 2)))
    await store.loadInitial()
    await store.loadMore()
    expect(calls).toHaveLength(1)
  })

  it('halaman kosong dari server menutup tombol (total disesuaikan), tanpa putaran tak berujung', async () => {
    const { store } = setup(({ url }) =>
      url.endsWith('offset=0') ? json(200, page([check(2), check(1)], 9)) : json(200, page([], 9, 2)),
    )
    await store.loadInitial()
    await store.loadMore()
    expect(store.getState().total).toBe(2)
  })

  it('loadMore saat sedang memuat diabaikan (tidak ada request ganda)', async () => {
    const gate = deferred<Response>()
    const { store, calls } = setup(({ url }) =>
      url.endsWith('offset=0') ? json(200, page([check(2), check(1)], 4)) : gate.promise,
    )
    await store.loadInitial()
    const first = store.loadMore()
    await store.loadMore()
    expect(calls).toHaveLength(2)
    gate.resolve(json(200, page([check(0)], 4, 2)))
    await first
  })
})

describe('submit', () => {
  it('berhasil: masuk paling atas, terpilih, total bertambah, POST berbadan JSON {ip}', async () => {
    const created = check(10, '1.1.1.1')
    const { store, calls } = setup(({ method }) =>
      method === 'POST' ? json(201, created) : json(200, page([check(2), check(1)], 2)),
    )
    await store.loadInitial()
    const ok = await store.submit('  1.1.1.1 ')
    expect(ok).toBe(true)
    const post = calls.find((c) => c.method === 'POST')
    expect(post?.url).toBe('/api/v1/checks')
    expect(post?.body).toEqual({ ip: '1.1.1.1' })
    const state = store.getState()
    expect(ids(state.history)).toEqual([10, 2, 1])
    expect(state.selected?.id).toBe(10)
    expect(state.total).toBe(3)
    expect(state.submitting).toBe(false)
    expect(state.submitError).toBeNull()
  })

  it('INPUT_DITOLAK: pesan dan reason_code tampil; riwayat dan panel tengah tidak berubah', async () => {
    const { store } = setup(({ method }) =>
      method === 'POST'
        ? json(422, {
            assessment_status: 'INPUT_DITOLAK',
            risk_score: null,
            reason_code: 'PRIVATE',
            message: 'Alamat privat/internal tidak diperiksa',
          })
        : json(200, page([check(2), check(1)], 2)),
    )
    await store.loadInitial()
    await store.select(2)
    const before = store.getState()
    expect(await store.submit('10.10.50.10')).toBe(false)
    const after = store.getState()
    expect(after.submitError).toEqual({
      kind: 'input_ditolak',
      message: 'Alamat privat/internal tidak diperiksa',
      reasonCode: 'PRIVATE',
    })
    expect(after.history).toBe(before.history)
    expect(after.selected).toBe(before.selected)
    expect(after.total).toBe(2)
    expect(after.submitting).toBe(false)
  })

  it('422 standar FastAPI menghasilkan pesan validasi, bukan INPUT_DITOLAK', async () => {
    const { store } = setup(() =>
      json(422, { detail: [{ type: 'missing', loc: ['body', 'ip'], msg: 'Field required' }] }),
    )
    await store.submit('abc')
    expect(store.getState().submitError).toEqual({
      kind: 'message',
      message: 'Input tidak valid: ip.',
    })
  })

  it('input kosong ditolak di browser tanpa request apa pun', async () => {
    const { store, calls } = setup(() => json(201, check(1)))
    expect(await store.submit('   ')).toBe(false)
    expect(calls).toHaveLength(0)
    expect(store.getState().submitError).toEqual({ kind: 'message', message: MESSAGE_EMPTY_IP })
  })

  it('submit kedua saat yang pertama masih berjalan diabaikan (satu POST saja)', async () => {
    const gate = deferred<Response>()
    const { store, calls } = setup(() => gate.promise)
    const first = store.submit('1.1.1.1')
    expect(store.getState().submitting).toBe(true)
    expect(await store.submit('1.1.1.1')).toBe(false)
    gate.resolve(json(201, check(1, '1.1.1.1')))
    expect(await first).toBe(true)
    expect(calls.filter((c) => c.method === 'POST')).toHaveLength(1)
  })

  it('cek ulang IP yang sama membuat baris baru (dedup per id, bukan per IP)', async () => {
    let next = 10
    const { store } = setup(({ method }) =>
      method === 'POST' ? json(201, check(next++, '8.8.8.8')) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit('8.8.8.8')
    await store.submit('8.8.8.8')
    expect(ids(store.getState().history)).toEqual([11, 10])
    expect(store.getState().history.every((c) => c.ip === '8.8.8.8')).toBe(true)
  })

  it('backend mati, 403, dan 5xx menampilkan pesan yang tepat', async () => {
    const down = setup(() => empty(502))
    await down.store.submit('1.1.1.1')
    expect(down.store.getState().submitError).toEqual({ kind: 'message', message: MESSAGE_UNREACHABLE })

    const forbidden = setup(() => json(403, { detail: 'Akses ditolak' }))
    await forbidden.store.submit('1.1.1.1')
    expect(forbidden.store.getState().submitError).toEqual({
      kind: 'message',
      message: 'Akses ditolak',
    })

    const broken = setup(() => new Response('Internal Server Error', { status: 500 }))
    await broken.store.submit('1.1.1.1')
    expect(broken.store.getState().submitError?.kind).toBe('message')
    expect(broken.store.getState().history).toEqual([])
  })

  it('401 mengakhiri sesi lewat klien dan TIDAK menampilkan pesan galat', async () => {
    const { store, onUnauthorized } = setup(() => json(401, { detail: 'x' }))
    await store.submit('1.1.1.1')
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    expect(store.getState().submitError).toBeNull()
    expect(store.getState().submitting).toBe(false)
  })

  it('request dibatalkan (logout) diabaikan diam-diam: tanpa galat, tanpa perubahan data', async () => {
    const calls: unknown[] = []
    const api = createApiClient({
      getToken: () => 'tok',
      onUnauthorized: vi.fn(),
      fetchImpl: ((_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          calls.push(1)
          init.signal?.addEventListener('abort', () => reject(new DOMException('x', 'AbortError')))
        })) as unknown as typeof fetch,
    })
    const store = createWorkbenchStore(api)
    const pending = store.submit('1.1.1.1')
    api.abortAll()
    expect(await pending).toBe(false)
    const state = store.getState()
    expect(state.submitError).toBeNull()
    expect(state.history).toEqual([])
    expect(state.selected).toBeNull()
    expect(state.submitting).toBe(false)
  })

  it('clearSubmitError menghapus pesan', async () => {
    const { store } = setup(() => empty(502))
    await store.submit('1.1.1.1')
    store.clearSubmitError()
    expect(store.getState().submitError).toBeNull()
  })
})

describe('select', () => {
  it('menampilkan baris riwayat langsung lalu menyegarkan lewat GET /checks/{id} tanpa cek ulang', async () => {
    const gate = deferred<Response>()
    const fresh = { ...check(2), checked_by: 'segar' }
    const { store, calls } = setup(({ url }) =>
      url.includes('/checks/2') ? gate.promise : json(200, page([check(3), check(2)], 2)),
    )
    await store.loadInitial()
    const pending = store.select(2)
    expect(store.getState().selected?.id).toBe(2)
    expect(store.getState().selected?.checked_by).toBe('tester')
    expect(store.getState().detailLoading).toBe(true)
    gate.resolve(json(200, fresh))
    await pending
    expect(store.getState().selected?.checked_by).toBe('segar')
    expect(store.getState().detailLoading).toBe(false)
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    expect(calls.map((c) => c.url)).toContain('/api/v1/checks/2')
  })

  it('klik A lalu B cepat-cepat: B yang terpilih walau respons A datang belakangan', async () => {
    const gateA = deferred<Response>()
    const gateB = deferred<Response>()
    const { store } = setup(({ url }) => {
      if (url.endsWith('/checks/1')) return gateA.promise
      if (url.endsWith('/checks/2')) return gateB.promise
      return json(200, page([check(2), check(1)], 2))
    })
    await store.loadInitial()
    const a = store.select(1)
    const b = store.select(2)
    gateB.resolve(json(200, check(2)))
    await b
    gateA.resolve(json(200, check(1)))
    await a
    expect(store.getState().selected?.id).toBe(2)
    expect(store.getState().detailLoading).toBe(false)
  })

  it('submit saat GET detail masih berjalan: hasil submit menang', async () => {
    const gate = deferred<Response>()
    const created = check(10, '1.1.1.1')
    const { store } = setup(({ method, url }) => {
      if (method === 'POST') return json(201, created)
      if (url.endsWith('/checks/1')) return gate.promise
      return json(200, page([check(1)], 1))
    })
    await store.loadInitial()
    const detail = store.select(1)
    await store.submit('1.1.1.1')
    gate.resolve(json(200, check(1)))
    await detail
    expect(store.getState().selected?.id).toBe(10)
  })

  it('404 menampilkan pesan dan mempertahankan pilihan sebelumnya', async () => {
    const { store } = setup(({ url }) => {
      if (url.endsWith('/checks/9')) return json(404, { detail: 'Cek tidak ditemukan' })
      if (url.endsWith('/checks/2')) return json(200, check(2))
      return json(200, page([check(2)], 1))
    })
    await store.loadInitial()
    await store.select(2)
    await store.select(9)
    const state = store.getState()
    expect(state.detailError).toBe('Pemeriksaan tidak ditemukan.')
    expect(state.selected?.id).toBe(2)
    expect(state.detailLoading).toBe(false)
  })

  it('id yang bukan bilangan bulat diabaikan (tidak ada request)', async () => {
    const { store, calls } = setup(() => json(200, check(1)))
    await store.select(Number.NaN)
    await store.select(1.5)
    expect(calls).toHaveLength(0)
  })
})

describe('balasan 2xx berbentuk salah ditolak di tepi (tidak merusak state)', () => {
  it('riwayat: objek bukan halaman', async () => {
    const { store } = setup(() => json(200, { hello: 'world' }))
    await store.loadInitial()
    expect(store.getState().historyStatus).toBe('error')
    expect(store.getState().historyError).toContain('tidak terbaca')
    expect(store.getState().history).toEqual([])
  })

  it('riwayat berikutnya: item rusak tidak ikut masuk', async () => {
    const { store } = setup(({ url }) =>
      url.endsWith('offset=0')
        ? json(200, page([check(2), check(1)], 5))
        : json(200, { items: [{ id: 'x' }], total: 5, limit: 20, offset: 2 }),
    )
    await store.loadInitial()
    await store.loadMore()
    expect(ids(store.getState().history)).toEqual([2, 1])
    expect(store.getState().historyError).toContain('tidak terbaca')
    expect(store.getState().loadingMore).toBe(false)
  })

  it('detail: pilihan sebelumnya dipertahankan', async () => {
    const { store } = setup(({ url }) =>
      url.endsWith('/checks/2') ? json(200, { items: [] }) : json(200, page([check(2)], 1)),
    )
    await store.loadInitial()
    await store.select(2)
    expect(store.getState().selected?.id).toBe(2)
    expect(store.getState().detailError).toContain('tidak terbaca')
    expect(store.getState().detailLoading).toBe(false)
  })

  it('submit: tidak ditambahkan ke riwayat dan pengguna diminta memeriksa riwayat', async () => {
    const { store } = setup(() => json(201, { sources: 'bukan array' }))
    expect(await store.submit('1.1.1.1')).toBe(false)
    const state = store.getState()
    expect(state.history).toEqual([])
    expect(state.selected).toBeNull()
    expect(state.submitError).toMatchObject({ kind: 'message' })
    expect(state.submitError?.message).toContain('Periksa riwayat')
    expect(state.submitting).toBe(false)
  })
})

describe('subscribe', () => {
  it('memberi tahu pendengar saat state berubah dan berhenti setelah unsubscribe', async () => {
    const { store } = setup(() => json(200, page([], 0)))
    const listener = vi.fn()
    const unsubscribe = store.subscribe(listener)
    await store.loadInitial()
    expect(listener).toHaveBeenCalled()
    const calls = listener.mock.calls.length
    unsubscribe()
    await store.loadInitial()
    expect(listener.mock.calls.length).toBe(calls)
  })
})
