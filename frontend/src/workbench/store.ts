import { createCheck, getCheck, listChecks } from '../api/checks'
import { isUnreachable, type ApiClient, type ApiFailure } from '../api/client'
import { isCheckOut, isCheckPage } from '../api/guards'
import type { CheckOut } from '../api/types'
import { parseCheckError } from '../lib/errors'
import { hasMore, mergeHistory, prependCheck } from '../lib/history'

// Logika alur kerja workbench tanpa framework: dipakai React lewat useSyncExternalStore dan diuji dengan
// klien API palsu (tanpa peramban). Satu store per sesi login (dibuat saat shell dimuat).

export type SubmitError =
  | { kind: 'input_ditolak'; message: string; reasonCode: string }
  | { kind: 'message'; message: string }

export interface WorkbenchState {
  history: CheckOut[]
  // Jumlah seluruh check di server dari respons terakhir; null sebelum riwayat pertama dimuat.
  total: number | null
  historyStatus: 'idle' | 'loading' | 'ready' | 'error'
  historyError: string | null
  loadingMore: boolean
  selected: CheckOut | null
  detailLoading: boolean
  detailError: string | null
  submitting: boolean
  submitError: SubmitError | null
}

export interface WorkbenchStore {
  getState: () => WorkbenchState
  subscribe: (listener: () => void) => () => void
  loadInitial: () => Promise<void>
  loadMore: () => Promise<void>
  select: (id: number) => Promise<void>
  // true bila pengecekan berhasil dibuat.
  submit: (ip: string) => Promise<boolean>
  clearSubmitError: () => void
}

export const MESSAGE_UNREACHABLE =
  'API tidak terjangkau. Pastikan backend berjalan, lalu coba lagi.'
export const MESSAGE_EMPTY_IP = 'Masukkan alamat IPv4 publik.'
export const MESSAGE_UNREADABLE = 'respons server tidak terbaca (bentuk data tidak sesuai).'

// null = tidak ada yang perlu ditampilkan: request dibatalkan (logout) atau 401 (sesi sudah diakhiri oleh klien).
export function failureMessage(failure: ApiFailure, subject: string): string | null {
  if (failure.kind === 'aborted' || failure.status === 401) return null
  if (isUnreachable(failure)) return MESSAGE_UNREACHABLE
  if (failure.status === 404) return `${subject} tidak ditemukan.`
  if (failure.status === 0 || failure.kind === 'invalid') {
    return `${subject} gagal dimuat: respons tidak terbaca.`
  }
  return `${subject} gagal dimuat (HTTP ${failure.status}).`
}

function submitErrorOf(failure: ApiFailure): SubmitError | null {
  if (failure.kind === 'aborted') return null
  const error = parseCheckError(failure)
  switch (error.kind) {
    case 'input_ditolak':
      return {
        kind: 'input_ditolak',
        message: error.message,
        reasonCode: error.reasonCode,
      }
    case 'unauthorized':
      return null
    case 'network':
      return { kind: 'message', message: MESSAGE_UNREACHABLE }
    case 'forbidden':
    case 'validation':
    case 'server':
    case 'unknown':
      return { kind: 'message', message: error.message }
  }
}

export function createWorkbenchStore(api: ApiClient): WorkbenchStore {
  let state: WorkbenchState = {
    history: [],
    total: null,
    historyStatus: 'idle',
    historyError: null,
    loadingMore: false,
    selected: null,
    detailLoading: false,
    detailError: null,
    submitting: false,
    submitError: null,
  }
  const listeners = new Set<() => void>()
  // Setiap pemilihan/pengecekan baru menaikkan token; respons detail dengan token lama diabaikan.
  let selectToken = 0

  function setState(patch: Partial<WorkbenchState>) {
    state = { ...state, ...patch }
    for (const listener of listeners) listener()
  }

  async function loadInitial() {
    if (state.historyStatus === 'loading') return
    setState({ historyStatus: 'loading', historyError: null })
    const result = await listChecks(api, 0)
    if (!result.ok) {
      if (result.kind === 'aborted') return
      setState({
        historyStatus: 'error',
        historyError: failureMessage(result, 'Riwayat'),
      })
      return
    }
    if (!isCheckPage(result.data)) {
      setState({ historyStatus: 'error', historyError: `Riwayat gagal dimuat: ${MESSAGE_UNREADABLE}` })
      return
    }
    // Check yang dibuat selagi memuat sudah ada di depan; sisanya digabung tanpa duplikat.
    const history = mergeHistory(state.history, result.data.items)
    setState({
      history,
      total: Math.max(result.data.total, history.length),
      historyStatus: 'ready',
    })
  }

  async function loadMore() {
    if (state.loadingMore || state.historyStatus !== 'ready') return
    if (!hasMore(state.history.length, state.total)) return
    setState({ loadingMore: true, historyError: null })
    // offset = jumlah yang sudah dimuat; baris yang bergeser karena check baru dibuang oleh dedup.
    const result = await listChecks(api, state.history.length)
    if (!result.ok) {
      if (result.kind === 'aborted') return
      setState({
        loadingMore: false,
        historyError: failureMessage(result, 'Riwayat'),
      })
      return
    }
    if (!isCheckPage(result.data)) {
      setState({ loadingMore: false, historyError: `Riwayat gagal dimuat: ${MESSAGE_UNREADABLE}` })
      return
    }
    const incoming = result.data.items
    const merged = mergeHistory(state.history, incoming)
    const added = merged.length - state.history.length
    setState({
      history: merged,
      // Server sudah tidak punya baris lagi: jangan biarkan tombol "Muat lagi" tertinggal.
      total:
        incoming.length === 0
          ? merged.length
          : Math.max(result.data.total, merged.length),
      loadingMore: false,
    })
    // Sebagian baris sudah ada = offset bergeser karena ada check baru dari orang lain. Baris terbaru itu
    // sendiri tidak pernah ikut termuat oleh paginasi, jadi ambil ulang halaman terdepan agar muncul di atas.
    if (added < incoming.length) {
      const gained = await refreshHead()
      // Tidak ada kemajuan sama sekali: tutup tombol alih-alih membiarkannya diklik tanpa efek.
      if (added === 0 && gained === 0) setState({ total: state.history.length })
    }
  }

  // Menambahkan check yang lebih baru dari yang sudah dimuat ke atas riwayat. Mengembalikan jumlah baris baru.
  // Kegagalan diam-diam diabaikan: ini penyegaran tambahan, bukan aksi yang diminta pengguna.
  async function refreshHead(): Promise<number> {
    const result = await listChecks(api, 0)
    if (!result.ok || !isCheckPage(result.data)) return 0
    const known = new Set(state.history.map((check) => check.id))
    const newcomers = result.data.items.filter((check) => !known.has(check.id))
    if (newcomers.length > 0) {
      const history = [...newcomers, ...state.history]
      setState({ history, total: Math.max(result.data.total, history.length) })
    }
    return newcomers.length
  }

  async function select(id: number) {
    if (!Number.isInteger(id)) return
    const token = ++selectToken
    // Baris riwayat sudah berisi CheckOut lengkap: tampilkan langsung, lalu segarkan lewat GET /checks/{id}.
    const known = state.history.find((check) => check.id === id) ?? null
    setState({
      selected: known ?? state.selected,
      detailLoading: true,
      detailError: null,
    })
    const result = await getCheck(api, id)
    if (token !== selectToken) return
    if (!result.ok) {
      if (result.kind === 'aborted') {
        setState({ detailLoading: false })
        return
      }
      setState({
        detailLoading: false,
        detailError: failureMessage(result, 'Pemeriksaan'),
      })
      return
    }
    if (!isCheckOut(result.data)) {
      setState({ detailLoading: false, detailError: `Pemeriksaan gagal dimuat: ${MESSAGE_UNREADABLE}` })
      return
    }
    setState({ selected: result.data, detailLoading: false })
  }

  async function submit(ip: string): Promise<boolean> {
    if (state.submitting) return false
    const trimmed = ip.trim()
    if (trimmed === '') {
      setState({ submitError: { kind: 'message', message: MESSAGE_EMPTY_IP } })
      return false
    }
    // Pengecekan baru mengalahkan GET detail yang masih berjalan.
    selectToken += 1
    setState({ submitting: true, submitError: null, detailLoading: false })
    const result = await createCheck(api, trimmed)
    if (!result.ok) {
      // INPUT_DITOLAK dan galat lain: panel tengah dan riwayat tidak berubah.
      setState({ submitting: false, submitError: submitErrorOf(result) })
      return false
    }
    if (!isCheckOut(result.data)) {
      // Server menjawab 2xx tetapi bentuknya salah: pengecekan mungkin sudah tersimpan di sisi server.
      setState({
        submitting: false,
        submitError: {
          kind: 'message',
          message: `Hasil pengecekan tidak terbaca: ${MESSAGE_UNREADABLE} Periksa riwayat sebelum mengulang.`,
        },
      })
      return false
    }
    setState({
      history: prependCheck(state.history, result.data),
      total: state.total === null ? null : state.total + 1,
      selected: result.data,
      detailError: null,
      submitting: false,
      submitError: null,
    })
    return true
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
    loadMore,
    select,
    submit,
    clearSubmitError: () => {
      if (state.submitError !== null) setState({ submitError: null })
    },
  }
}
