import { describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../api/client'
import type { IocOut, IocPage } from '../api/types'
import { makeIoc } from '../testing/fixtures'
import { createMispStore, MESSAGE_UNREADABLE_SEND } from './mispStore'
import { MESSAGE_UNREACHABLE } from './store'

const page = (items: IocOut[], total: number, offset = 0): IocPage => ({
  items,
  total,
  limit: 100,
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
  return { store: createMispStore(api), calls, onUnauthorized }
}

const ids = (list: IocOut[]) => list.map((item) => item.id)
const posts = (calls: Call[]) => calls.filter((call) => call.method === 'POST')
const REASON = 'alasan pengiriman yang cukup panjang'

// Server palsu: GET /iocs mengembalikan `server`, POST menjalankan `onPost`.
function fakeServer(
  initial: IocOut[],
  onPost: (call: Call, server: { items: IocOut[] }) => Response | Promise<Response>,
) {
  const server = { items: [...initial] }
  return {
    server,
    handler: (call: Call) =>
      call.method === 'POST'
        ? onPost(call, server)
        : json(200, page(server.items, server.items.length)),
  }
}

describe('loadInitial', () => {
  it('memuat 100 kiriman terbaru dari offset 0', async () => {
    const { store, calls } = setup(() => json(200, page([makeIoc({ id: 2 }), makeIoc({ id: 1 })], 2)))
    await store.loadInitial()
    expect(calls[0].url).toBe('/api/v1/iocs?limit=100&offset=0')
    expect(ids(store.getState().items)).toEqual([2, 1])
    expect(store.getState().status).toBe('ready')
    expect(store.getState().total).toBe(2)
  })

  it('backend mati (502 kosong): status error dengan pesan tidak terjangkau', async () => {
    const { store } = setup(() => empty(502))
    await store.loadInitial()
    expect(store.getState().status).toBe('error')
    expect(store.getState().error).toBe(MESSAGE_UNREACHABLE)
    expect(store.getState().items).toEqual([])
  })

  it('bentuk respons salah (status tak dikenal): ditolak, tidak ditampilkan sebagai sukses', async () => {
    const bad = { ...makeIoc({ id: 1 }), status: 'delivered' }
    const { store } = setup(() => json(200, { items: [bad], total: 1, limit: 100, offset: 0 }))
    await store.loadInitial()
    expect(store.getState().status).toBe('error')
    expect(store.getState().items).toEqual([])
  })

  it('401 memicu logout global dan tidak menampilkan pesan', async () => {
    const { store, onUnauthorized } = setup(() => json(401, { detail: 'Not authenticated' }))
    await store.loadInitial()
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    expect(store.getState().error).toBeNull()
  })

  it('coba lagi setelah error memuat ulang', async () => {
    let fail = true
    const { store } = setup(() => (fail ? empty(502) : json(200, page([makeIoc({ id: 1 })], 1))))
    await store.loadInitial()
    fail = false
    await store.refresh()
    expect(store.getState().status).toBe('ready')
    expect(ids(store.getState().items)).toEqual([1])
  })
})

describe('submit: berhasil', () => {
  it('201 mock_sent: baris masuk, daftar dimuat ulang, mengirim body yang benar', async () => {
    const { handler, server } = fakeServer([], (call, srv) => {
      const body = call.body as { check_id: number }
      const created = makeIoc({ id: 11, check_id: body.check_id })
      srv.items = [created, ...srv.items]
      return json(201, created)
    })
    const { store, calls } = setup(handler)
    await store.loadInitial()
    const ok = await store.submit(5, REASON, ['tlp:amber'])
    expect(ok).toBe(true)
    expect(posts(calls)).toHaveLength(1)
    expect(posts(calls)[0].url).toBe('/api/v1/iocs/misp')
    expect(posts(calls)[0].body).toEqual({ check_id: 5, reason: REASON, tags: ['tlp:amber'] })
    // GET awal + GET penyegaran setelah kirim
    expect(calls.filter((c) => c.method === 'GET')).toHaveLength(2)
    expect(ids(store.getState().items)).toEqual([11])
    expect(store.getState().items[0].status).toBe('mock_sent')
    expect(store.getState().total).toBe(1)
    expect(store.getState().sendingIds).toEqual([])
    expect(server.items).toHaveLength(1)
  })

  it('kirim ulang dari failed (200): baris yang sama diperbarui, tidak ada baris ganda', async () => {
    const failed = makeIoc({ id: 4, check_id: 9, status: 'failed', misp_event_uuid: null, error_message: 'gagal' })
    const { handler } = fakeServer([failed], (_call, srv) => {
      const fixed = makeIoc({ id: 4, check_id: 9, status: 'mock_sent' })
      srv.items = [fixed]
      return json(200, fixed)
    })
    const { store } = setup(handler)
    await store.loadInitial()
    expect(await store.submit(9, REASON, [])).toBe(true)
    expect(ids(store.getState().items)).toEqual([4])
    expect(store.getState().items[0].status).toBe('mock_sent')
    expect(store.getState().total).toBe(1)
  })
})

describe('submit: klik ganda dan beberapa check', () => {
  it('klik kedua saat request berjalan tidak mengirim POST kedua', async () => {
    const gate = deferred<Response>()
    const { store, calls } = setup((call) =>
      call.method === 'POST' ? gate.promise : json(200, page([], 0)),
    )
    await store.loadInitial()
    const first = store.submit(5, REASON, [])
    const second = await store.submit(5, REASON, [])
    expect(second).toBe(false)
    expect(posts(calls)).toHaveLength(1)
    gate.resolve(json(201, makeIoc({ id: 1, check_id: 5 })))
    expect(await first).toBe(true)
    expect(posts(calls)).toHaveLength(1)
  })

  it('status "mengirim" dipegang per check: check lain tidak ikut terkunci', async () => {
    const gate = deferred<Response>()
    const { store } = setup((call) =>
      call.method === 'POST' ? gate.promise : json(200, page([], 0)),
    )
    await store.loadInitial()
    const pending = store.submit(5, REASON, [])
    expect(store.getState().sendingIds).toEqual([5])
    expect(store.getState().sendingIds.includes(6)).toBe(false)
    gate.resolve(json(201, makeIoc({ id: 1, check_id: 5 })))
    await pending
    expect(store.getState().sendingIds).toEqual([])
  })

  it('jawaban yang datang belakangan memperbarui check yang benar walau pengguna sudah berpindah', async () => {
    const gate = deferred<Response>()
    const { store } = setup((call) =>
      call.method === 'POST' ? gate.promise : json(200, page([], 0)),
    )
    await store.loadInitial()
    const pending = store.submit(5, REASON, [])
    // pengguna berpindah ke check 6 dan mulai mengirim juga (tidak terblokir)
    const other = store.submit(6, REASON, [])
    expect(store.getState().sendingIds).toEqual([5, 6])
    gate.resolve(json(201, makeIoc({ id: 1, check_id: 5 })))
    await Promise.all([pending, other])
    expect(store.getState().items.some((item) => item.check_id === 5)).toBe(true)
  })
})

describe('submit: 409 bukan galat', () => {
  it('memuat ulang dan menampilkan kiriman yang sudah ada tanpa pesan galat', async () => {
    const existing = makeIoc({ id: 8, check_id: 5 })
    let loaded = false
    const { store } = setup((call) => {
      if (call.method === 'POST') {
        loaded = true
        return json(409, { detail: 'Check ini sudah pernah dikirim ke MISP', submission_id: 8 })
      }
      return json(200, page(loaded ? [existing] : [], loaded ? 1 : 0))
    })
    await store.loadInitial()
    expect(await store.submit(5, REASON, [])).toBe(false)
    expect(ids(store.getState().items)).toEqual([8])
    expect(store.getState().issues[5]).toBeUndefined()
  })

  it('kiriman di luar 100 terbaru: keterangan netral (info), bukan galat merah', async () => {
    const { store } = setup((call) =>
      call.method === 'POST'
        ? json(409, { detail: 'Check ini sudah pernah dikirim ke MISP', submission_id: 8 })
        : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    const issue = store.getState().issues[5]
    expect(issue.kind).toBe('info')
    expect(issue.message).toContain('Check ini sudah pernah dikirim ke MISP')
    expect(issue.message).toContain('#8')
  })
})

describe('submit: kegagalan', () => {
  it('501 (MISP_MODE=live belum ada): baris failed masuk daftar, bukan sukses, bukan galat generik', async () => {
    const failed = makeIoc({
      id: 3,
      check_id: 5,
      status: 'failed',
      misp_event_uuid: null,
      error_message: 'MISP_MODE=live belum diimplementasikan; gunakan MISP_MODE=mock',
    })
    const { store } = setup((call) =>
      call.method === 'POST' ? json(501, failed) : json(200, page([failed], 1)),
    )
    await store.loadInitial()
    expect(await store.submit(5, REASON, [])).toBe(false)
    const item = store.getState().items[0]
    expect(item.status).toBe('failed')
    expect(item.error_message).toContain('MISP_MODE=live')
    expect(store.getState().issues[5]).toBeUndefined()
    expect(store.getState().sendingIds).toEqual([])
  })

  it('502 dari MISP: baris failed masuk; total bertambah satu', async () => {
    const failed = makeIoc({ id: 3, check_id: 5, status: 'failed', misp_event_uuid: null, error_message: 'x' })
    const { store } = setup((call) =>
      call.method === 'POST' ? json(502, failed) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    expect(ids(store.getState().items)).toEqual([3])
    expect(store.getState().items[0].status).toBe('failed')
  })

  it('422 alasan/simulasi (detail teks): pesan backend dekat form', async () => {
    const detail = 'Cek ini berisi hasil simulasi (SUMBER_SIMULASI) dan tidak boleh dikirim ke MISP'
    const { store } = setup((call) =>
      call.method === 'POST' ? json(422, { detail }) : json(200, page([], 0)),
    )
    await store.loadInitial()
    expect(await store.submit(5, REASON, [])).toBe(false)
    expect(store.getState().issues[5]).toEqual({ kind: 'error', message: detail })
    expect(store.getState().items).toEqual([])
  })

  it('422 validasi FastAPI (detail array): hanya nama field, tanpa menyalin input', async () => {
    const { store } = setup((call) =>
      call.method === 'POST'
        ? json(422, {
            detail: [{ loc: ['body', 'reason'], msg: 'terlalu pendek', input: 'RAHASIA-ISIAN', type: 'x' }],
          })
        : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    const message = store.getState().issues[5].message
    expect(message).toBe('Input tidak valid: reason.')
    expect(message).not.toContain('RAHASIA')
  })

  it('403: "Akun ini tidak berhak mengirim ke MISP"', async () => {
    const { store } = setup((call) =>
      call.method === 'POST' ? json(403, { detail: 'Forbidden' }) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    expect(store.getState().issues[5]).toEqual({
      kind: 'error',
      message: 'Akun ini tidak berhak mengirim ke MISP',
    })
  })

  it('404: check tidak ditemukan ditampilkan', async () => {
    const { store } = setup((call) =>
      call.method === 'POST' ? json(404, { detail: 'Cek tidak ditemukan' }) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    expect(store.getState().issues[5]).toEqual({ kind: 'error', message: 'Cek tidak ditemukan' })
  })

  it('backend mati saat kirim (502 kosong): pesan tidak terjangkau', async () => {
    const { store } = setup((call) =>
      call.method === 'POST' ? empty(502) : json(200, page([], 0)),
    )
    await store.loadInitial()
    expect(await store.submit(5, REASON, [])).toBe(false)
    expect(store.getState().issues[5]).toEqual({ kind: 'error', message: MESSAGE_UNREACHABLE })
  })

  it('500 tanpa badan: pesan server', async () => {
    const { store } = setup((call) =>
      call.method === 'POST' ? empty(500) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    expect(store.getState().issues[5].kind).toBe('error')
  })

  it('401: logout global, tanpa pesan di form', async () => {
    const { store, onUnauthorized } = setup((call) =>
      call.method === 'POST' ? json(401, { detail: 'x' }) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    expect(store.getState().issues[5]).toBeUndefined()
  })

  it('201 dengan bentuk salah: tidak dianggap sukses, menyuruh memeriksa Kiriman MISP', async () => {
    const { store } = setup((call) =>
      call.method === 'POST' ? json(201, { ok: true }) : json(200, page([], 0)),
    )
    await store.loadInitial()
    expect(await store.submit(5, REASON, [])).toBe(false)
    expect(store.getState().issues[5]).toEqual({ kind: 'error', message: MESSAGE_UNREADABLE_SEND })
    expect(store.getState().items).toEqual([])
  })

  it('status sending selalu kembali kosong setelah kegagalan, sehingga bisa dicoba lagi', async () => {
    const { store, calls } = setup((call) =>
      call.method === 'POST' ? empty(502) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    await store.submit(5, REASON, [])
    expect(posts(calls)).toHaveLength(2)
  })

  it('mengubah isian (clearIssue) menghapus keterangan hanya untuk check itu', async () => {
    const { store } = setup((call) =>
      call.method === 'POST' ? json(403, { detail: 'x' }) : json(200, page([], 0)),
    )
    await store.loadInitial()
    await store.submit(5, REASON, [])
    await store.submit(6, REASON, [])
    store.clearIssue(5)
    expect(store.getState().issues[5]).toBeUndefined()
    expect(store.getState().issues[6]).toBeDefined()
  })
})

describe('refresh dan loadMore', () => {
  it('refresh setelah ready memperbarui status baris tanpa mengubah tampilan bila gagal', async () => {
    let pending = true
    let down = false
    const { store } = setup(() =>
      down
        ? empty(502)
        : json(200, page([makeIoc({ id: 1, status: pending ? 'pending' : 'mock_sent' })], 1)),
    )
    await store.loadInitial()
    pending = false
    await store.refresh()
    expect(store.getState().items[0].status).toBe('mock_sent')
    down = true
    await store.refresh()
    expect(store.getState().status).toBe('ready')
    expect(store.getState().error).toBeNull()
    expect(store.getState().items[0].status).toBe('mock_sent')
  })

  it('loadMore memakai offset = jumlah dimuat dan dedup per id', async () => {
    const { store, calls } = setup(({ url }) =>
      url.endsWith('offset=0')
        ? json(200, page([makeIoc({ id: 5 }), makeIoc({ id: 4 }), makeIoc({ id: 3 })], 6))
        : json(200, page([makeIoc({ id: 3 }), makeIoc({ id: 2 }), makeIoc({ id: 1 })], 7, 3)),
    )
    await store.loadInitial()
    await store.loadMore()
    expect(calls[1].url).toBe('/api/v1/iocs?limit=100&offset=3')
    expect(ids(store.getState().items)).toEqual([5, 4, 3, 2, 1])
    expect(store.getState().total).toBe(7)
  })

  it('tidak memanggil server bila semua sudah dimuat', async () => {
    const { store, calls } = setup(() => json(200, page([makeIoc({ id: 1 })], 1)))
    await store.loadInitial()
    await store.loadMore()
    expect(calls).toHaveLength(1)
  })

  it('tidak macet: halaman berikutnya hanya berisi baris yang sudah dimuat, tombol ditutup', async () => {
    const { store } = setup(() => json(200, page([makeIoc({ id: 2 }), makeIoc({ id: 1 })], 5)))
    await store.loadInitial()
    await store.loadMore()
    expect(store.getState().total).toBe(store.getState().items.length)
    expect(store.getState().loadingMore).toBe(false)
  })

  it('kiriman baru dari orang lain: halaman terdepan diambil ulang agar muncul di atas', async () => {
    let calls = 0
    const { store } = setup(({ url }) => {
      calls += 1
      if (calls === 1) return json(200, page([makeIoc({ id: 3 }), makeIoc({ id: 2 })], 3))
      if (url.endsWith('offset=2')) return json(200, page([makeIoc({ id: 2 }), makeIoc({ id: 1 })], 4, 2))
      return json(200, page([makeIoc({ id: 4 }), makeIoc({ id: 3 })], 4))
    })
    await store.loadInitial()
    await store.loadMore()
    expect(ids(store.getState().items)).toEqual([4, 3, 2, 1])
  })
})
