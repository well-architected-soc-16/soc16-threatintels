import { IOC_PAGE_SIZE, listIocs, submitIoc } from '../api/iocs'
import type { ApiClient } from '../api/client'
import { isIocOut, isIocPage } from '../api/guards'
import type { IocOut } from '../api/types'
import { parseIocError } from '../lib/errors'
import { hasMore } from '../lib/history'
import {
  appendPage,
  applyHead,
  findSubmissionForCheck,
  upsertSubmission,
} from '../lib/misp'
import { MESSAGE_UNREACHABLE, MESSAGE_UNREADABLE, failureMessage } from './store'

// Alur kirim ke MISP tanpa framework (pola sama dengan createWorkbenchStore). Menyimpan daftar kiriman
// (GET /iocs, 100 terbaru dimuat di awal) yang dipakai dua hal: status per check/IP di rel keputusan dan
// tabel Kiriman MISP. Satu store per sesi login.

// 'error' = kegagalan nyata (merah); 'info' = bukan kegagalan, hanya keterangan (netral).
export interface SendIssue {
  kind: 'error' | 'info'
  message: string
}

export interface MispState {
  items: IocOut[]
  total: number | null
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  loadingMore: boolean
  // Check yang sedang dikirim. Per check, bukan satu bendera global: berpindah check saat kirim berjalan
  // tidak boleh membuat check lain tampak "Mengirim…".
  sendingIds: readonly number[]
  // Keterangan hasil kirim terakhir per check (yang sukses/gagal ditampilkan dari baris kirimannya sendiri).
  issues: Readonly<Record<number, SendIssue>>
}

export interface MispStore {
  getState: () => MispState
  subscribe: (listener: () => void) => () => void
  loadInitial: () => Promise<void>
  // Segarkan halaman terdepan tanpa mengubah tampilan bila gagal (masuk ke tampilan Kiriman MISP, tombol segarkan).
  refresh: () => Promise<void>
  loadMore: () => Promise<void>
  // true bila kiriman baru berhasil dibuat/dikirim ulang.
  submit: (checkId: number, reason: string, tags: string[]) => Promise<boolean>
  clearIssue: (checkId: number) => void
}

export const MESSAGE_UNREADABLE_SEND =
  'Hasil kiriman tidak terbaca: respons server tidak sesuai bentuk. Periksa tampilan Kiriman MISP sebelum mengulang.'

function withoutKey(
  record: Readonly<Record<number, SendIssue>>,
  key: number,
): Record<number, SendIssue> {
  return Object.fromEntries(Object.entries(record).filter(([id]) => Number(id) !== key))
}

export function createMispStore(api: ApiClient): MispStore {
  let state: MispState = {
    items: [],
    total: null,
    status: 'idle',
    error: null,
    loadingMore: false,
    sendingIds: [],
    issues: {},
  }
  const listeners = new Set<() => void>()

  function setState(patch: Partial<MispState>) {
    state = { ...state, ...patch }
    for (const listener of listeners) listener()
  }

  function setIssue(checkId: number, issue: SendIssue | null) {
    if (issue === null) {
      if (checkId in state.issues) setState({ issues: withoutKey(state.issues, checkId) })
      return
    }
    setState({ issues: { ...state.issues, [checkId]: issue } })
  }

  async function loadInitial() {
    if (state.status === 'loading') return
    setState({ status: 'loading', error: null })
    const result = await listIocs(api, 0)
    if (!result.ok) {
      if (result.kind === 'aborted') return
      setState({ status: 'error', error: failureMessage(result, 'Daftar kiriman MISP') })
      return
    }
    if (!isIocPage(result.data)) {
      setState({
        status: 'error',
        error: `Daftar kiriman MISP gagal dimuat: ${MESSAGE_UNREADABLE}`,
      })
      return
    }
    const items = applyHead(state.items, result.data.items)
    setState({
      items,
      total: Math.max(result.data.total, items.length),
      status: 'ready',
    })
  }

  // Mengembalikan jumlah baris baru. Kegagalan diabaikan: ini penyegaran tambahan, bukan aksi yang diminta.
  async function refreshHead(): Promise<number> {
    const result = await listIocs(api, 0)
    if (!result.ok || !isIocPage(result.data)) return 0
    const known = new Set(state.items.map((item) => item.id))
    const gained = result.data.items.filter((item) => !known.has(item.id)).length
    const items = applyHead(state.items, result.data.items)
    // Total tidak pernah turun karena penyegaran (kiriman tidak dihapus); jawaban yang lebih lama tidak boleh menyusutkannya.
    setState({ items, total: Math.max(state.total ?? 0, result.data.total, items.length) })
    return gained
  }

  async function refresh() {
    if (state.status === 'error' || state.status === 'idle') {
      await loadInitial()
      return
    }
    await refreshHead()
  }

  async function loadMore() {
    if (state.loadingMore || state.status !== 'ready') return
    if (!hasMore(state.items.length, state.total)) return
    setState({ loadingMore: true, error: null })
    // offset = jumlah yang sudah dimuat; baris yang bergeser karena kiriman baru dibuang oleh dedup.
    const result = await listIocs(api, state.items.length)
    if (!result.ok) {
      if (result.kind === 'aborted') return
      setState({ loadingMore: false, error: failureMessage(result, 'Daftar kiriman MISP') })
      return
    }
    if (!isIocPage(result.data)) {
      setState({
        loadingMore: false,
        error: `Daftar kiriman MISP gagal dimuat: ${MESSAGE_UNREADABLE}`,
      })
      return
    }
    const incoming = result.data.items
    const merged = appendPage(state.items, incoming)
    const added = merged.length - state.items.length
    setState({
      items: merged,
      // Server sudah tidak punya baris lagi: jangan biarkan tombol "Muat lagi" tertinggal.
      total:
        incoming.length === 0
          ? merged.length
          : Math.max(result.data.total, merged.length),
      loadingMore: false,
    })
    // Sebagian baris sudah ada = offset bergeser karena kiriman baru dari orang lain; ambil halaman terdepan
    // agar baris terbaru itu muncul. Tanpa kemajuan sama sekali: tutup tombol alih-alih membiarkannya tanpa efek.
    if (added < incoming.length) {
      const gained = await refreshHead()
      if (added === 0 && gained === 0) setState({ total: state.items.length })
    }
  }

  async function submit(checkId: number, reason: string, tags: string[]): Promise<boolean> {
    if (state.sendingIds.includes(checkId)) return false
    setState({ sendingIds: [...state.sendingIds, checkId] })
    setIssue(checkId, null)
    try {
      const result = await submitIoc(api, { check_id: checkId, reason, tags })

      if (result.ok) {
        if (!isIocOut(result.data)) {
          // 2xx tetapi bentuknya salah: kiriman mungkin sudah tersimpan di server.
          setIssue(checkId, { kind: 'error', message: MESSAGE_UNREADABLE_SEND })
          await refreshHead()
          return false
        }
        const item = result.data
        const isNew = !state.items.some((candidate) => candidate.id === item.id)
        setState({
          items: upsertSubmission(state.items, item),
          total: isNew && state.total !== null ? state.total + 1 : state.total,
        })
        // Server adalah sumber kebenaran: segarkan daftar setelah setiap kirim.
        await refreshHead()
        return true
      }

      if (result.kind === 'aborted') return false
      const error = parseIocError(result)
      switch (error.kind) {
        case 'unauthorized':
          return false
        case 'failed': {
          // 501/502: kiriman tersimpan sebagai `failed`. Ditampilkan dari barisnya (merah), form tetap terisi.
          const submission = error.submission
          const isNew = !state.items.some((candidate) => candidate.id === submission.id)
          setState({
            items: upsertSubmission(state.items, submission),
            total: isNew && state.total !== null ? state.total + 1 : state.total,
          })
          await refreshHead()
          return false
        }
        case 'duplicate':
          // 409 bukan galat: kiriman sudah ada, muat ulang dan tampilkan.
          await refreshHead()
          if (findSubmissionForCheck(state.items, checkId) === null) {
            setIssue(checkId, {
              kind: 'info',
              message: `${error.message} (kiriman #${error.submissionId}). Kiriman itu tidak ada di ${IOC_PAGE_SIZE} kiriman terbaru yang dimuat.`,
            })
          }
          return false
        case 'network':
          setIssue(checkId, { kind: 'error', message: MESSAGE_UNREACHABLE })
          return false
        case 'not_found':
        case 'rejected':
        case 'validation':
        case 'forbidden':
        case 'server':
        case 'unknown':
          setIssue(checkId, { kind: 'error', message: error.message })
          return false
      }
    } finally {
      setState({ sendingIds: state.sendingIds.filter((id) => id !== checkId) })
    }
  }

  return {
    getState: () => state,
    subscribe: (listener) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    loadInitial,
    refresh,
    loadMore,
    submit,
    clearIssue: (checkId) => setIssue(checkId, null),
  }
}

