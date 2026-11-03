import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { IocOut } from '../api/types'
import { mispDeniedText } from '../lib/can'
import { DEMO_CHECKS, makeCheck, makeIoc } from '../testing/fixtures'
import type { MispState } from '../workbench/mispStore'
import { DecisionRail } from './DecisionRail'
import { MispFormView, MispPanel, SubmissionView } from './MispPanel'
import { MispView } from './MispView'

// Render markup (tanpa peramban) untuk invarian Aturan tampilan 4-8 pada alur MISP. Fixture SINTETIS.

const html = (node: React.ReactNode) => renderToStaticMarkup(node)
const noop = () => {}
const asyncNoop = () => Promise.resolve(true)

const live = makeCheck({ id: 3, ip: '118.25.6.39', flags: [], indication: 'RENDAH', risk_score: 4 })

type MispSlice = Pick<MispState, 'items' | 'status' | 'error' | 'sendingIds' | 'issues'>
const ready = (items: IocOut[], over: Partial<MispSlice> = {}): MispSlice => ({
  items,
  status: 'ready',
  error: null,
  sendingIds: [],
  issues: {},
  ...over,
})

const ANALYST_OK = null
const VIEWER = mispDeniedText({ role: 'viewer', can_send_misp: false, is_active: true })
const ANALYST_NO = mispDeniedText({ role: 'analyst', can_send_misp: false, is_active: true })

function panel(misp: MispSlice, deniedText: string | null = ANALYST_OK, check = live) {
  return html(
    <MispPanel
      check={check}
      misp={misp}
      deniedText={deniedText}
      onSubmit={asyncNoop}
      onClearIssue={noop}
      onRetryLoad={noop}
    />,
  )
}

const NO_GREEN = /green|emerald|lime|teal/
const NO_PERCENT = /%/

describe('teks izin (mispDeniedText)', () => {
  it('admin dan analyst berizin: null; analyst tanpa izin dan viewer: teks berbeda', () => {
    expect(mispDeniedText({ role: 'admin', can_send_misp: false, is_active: true })).toBeNull()
    expect(mispDeniedText({ role: 'analyst', can_send_misp: true, is_active: true })).toBeNull()
    expect(ANALYST_NO).toBe('Kirim ke MISP butuh izin dari admin.')
    expect(VIEWER).toContain('tidak dapat mengirim ke MISP')
    expect(mispDeniedText(null)).not.toBeNull()
  })
})

describe('DecisionRail: bagian MISP', () => {
  const slot = <p>ISI-PANEL-MISP</p>

  it('check simulasi: hanya teks larangan, panel MISP tidak dirender sama sekali', () => {
    const out = html(
      <DecisionRail check={DEMO_CHECKS['1.1.1.1']} canRun submitting={false} onRerun={noop} misp={slot} />,
    )
    expect(out).toContain('Hasil simulasi tidak boleh dikirim ke MISP.')
    expect(out).not.toContain('ISI-PANEL-MISP')
  })

  it('check live: panel MISP dirender; placeholder "tahap berikutnya" sudah hilang', () => {
    const out = html(<DecisionRail check={live} canRun submitting={false} onRerun={noop} misp={slot} />)
    expect(out).toContain('ISI-PANEL-MISP')
    expect(out).not.toContain('tahap berikutnya')
    expect(out).not.toContain('tidak boleh dikirim ke MISP')
  })
})

describe('MispPanel: memuat status kiriman', () => {
  it('sedang memuat: tanpa form, tanpa tombol kirim', () => {
    const out = panel({ ...ready([]), status: 'loading' })
    expect(out).toContain('Memuat status kiriman…')
    expect(out).not.toContain('<form')
    expect(out).not.toContain('Kirim ke MISP')
  })

  it('gagal memuat: pesan merah + "Coba lagi", form TIDAK ditampilkan (konfirmasi IP yang sama akan terlewat)', () => {
    const out = panel({ ...ready([]), status: 'error', error: 'API tidak terjangkau.' })
    expect(out).toContain('role="alert"')
    expect(out).toContain('API tidak terjangkau.')
    expect(out).toContain('Coba lagi')
    expect(out).not.toContain('<form')
    expect(out).not.toContain('textarea')
  })
})

describe('MispPanel: belum ada kiriman', () => {
  it('akun berizin: form dengan alasan, tag, penghitung, tombol, dan catatan "tidak memblokir IP"', () => {
    const out = panel(ready([]))
    expect(out).toContain('<form')
    expect(out).toContain('id="misp-reason"')
    expect(out).toContain('id="misp-tags"')
    expect(out).toContain('0/2000 karakter, minimal 10')
    expect(out).toContain('Kirim ke MISP')
    expect(out).toContain('Pengiriman manual. Tidak memblokir IP.')
    expect(out).not.toContain('duplikat')
    expect(out).not.toMatch(NO_GREEN)
  })

  it('viewer: teks, tanpa form dan tanpa tombol', () => {
    const out = panel(ready([]), VIEWER)
    expect(out).toContain(VIEWER)
    expect(out).not.toContain('<form')
    expect(out).not.toContain('<button')
  })

  it('analyst tanpa can_send_misp: "butuh izin dari admin", tanpa form', () => {
    const out = panel(ready([]), ANALYST_NO)
    expect(out).toContain('Kirim ke MISP butuh izin dari admin.')
    expect(out).not.toContain('<form')
  })

  it('IP sama sudah dikirim lewat check lain: form biasa dulu (konfirmasi baru muncul setelah klik)', () => {
    const previous = makeIoc({ id: 1, check_id: 2, ip: '118.25.6.39' })
    const out = panel(ready([previous]))
    expect(out).toContain('Kirim ke MISP')
    expect(out).not.toContain('sudah pernah dikirim lewat')
  })
})

describe('MispFormView: konfirmasi inline dan galat', () => {
  const base = {
    mode: 'new' as const,
    reason: 'alasan pengiriman yang cukup panjang',
    tagsText: '',
    onReason: noop,
    onTags: noop,
    reasonError: null,
    tagsError: null,
    previous: null,
    confirming: false,
    sending: false,
    issue: null,
    onSend: noop,
    onConfirm: noop,
    onCancel: noop,
  }

  it('konfirmasi: teks Keputusan 14 persis, dua tombol, kolom terkunci, tanpa kata "duplikat"', () => {
    const out = html(
      <MispFormView {...base} previous={makeIoc({ id: 1, check_id: 2, status: 'mock_sent' })} confirming />,
    )
    expect(out).toContain(
      'IP ini sudah pernah dikirim lewat check #2 (mock_sent). Kirim lagi sebagai catatan baru?',
    )
    expect(out).toContain('Kirim lagi sebagai catatan baru')
    expect(out).toContain('Batal')
    expect(out).not.toContain('>Kirim ke MISP<')
    expect(out).toContain('readOnly')
    expect(out.toLowerCase()).not.toContain('duplikat')
  })

  it('tanpa kiriman sebelumnya, confirming diabaikan', () => {
    const out = html(<MispFormView {...base} confirming />)
    expect(out).toContain('Kirim ke MISP')
    expect(out).not.toContain('Batal')
  })

  it('mengirim: tombol "Mengirim…" nonaktif', () => {
    const out = html(<MispFormView {...base} sending />)
    expect(out).toContain('Mengirim…')
    expect(out).toMatch(/<button[^>]*\sdisabled=""[^>]*>Mengirim…/)
  })

  it('mode kirim ulang: tombol "Kirim ulang"', () => {
    const out = html(<MispFormView {...base} mode="retry" />)
    expect(out).toContain('Kirim ulang')
    expect(out).not.toContain('Kirim ke MISP<')
  })

  it('alasan pendek: pesan inline, aria-invalid, tombol tetap aktif', () => {
    const out = html(
      <MispFormView {...base} reason="abcde" reasonError="Alasan minimal 10 karakter (sekarang 5)." />,
    )
    expect(out).toContain('Alasan minimal 10 karakter (sekarang 5).')
    expect(out).toContain('aria-invalid="true"')
    expect(out).toContain('aria-describedby="misp-reason-count misp-reason-error"')
    expect(out).toMatch(/<button type="submit"/)
    expect(out).not.toMatch(/<button[^>]*\sdisabled=""/)
  })

  it('galat kirim (merah) dengan role=alert; keterangan info netral tanpa merah', () => {
    const error = html(<MispFormView {...base} issue={{ kind: 'error', message: 'Akun ini tidak berhak mengirim ke MISP' }} />)
    expect(error).toContain('role="alert"')
    expect(error).toContain('border-gagal')
    expect(error).toContain('Akun ini tidak berhak mengirim ke MISP')
    const info = html(<MispFormView {...base} issue={{ kind: 'info', message: 'Sudah pernah dikirim (kiriman #8).' }} />)
    expect(info).toContain('Sudah pernah dikirim (kiriman #8).')
    expect(info).not.toContain('border-gagal')
    expect(info).not.toContain('role="alert"')
  })

  it('penghitung memangkas spasi dan menghitung code point', () => {
    const out = html(<MispFormView {...base} reason={'  😀😀😀  '} />)
    expect(out).toContain('3/2000 karakter')
  })
})

describe('MispPanel: kiriman yang sudah ada', () => {
  it('mock_sent: "Terkirim (mock)" + uuid MOCK-, BUKAN "Terkirim ke MISP", tanpa form', () => {
    const out = panel(ready([makeIoc({ id: 1, check_id: 3, status: 'mock_sent' })]))
    expect(out).toContain('Terkirim (mock)')
    expect(out).not.toContain('Terkirim ke MISP')
    expect(out).toContain('MOCK-')
    expect(out).toContain('Oleh')
    expect(out).toContain('analis_misp')
    expect(out).not.toContain('<form')
    expect(out).not.toContain('Kirim ke MISP')
    expect(out).not.toMatch(NO_GREEN)
  })

  it('sent: "Terkirim ke MISP" netral', () => {
    const out = panel(ready([makeIoc({ id: 1, check_id: 3, status: 'sent' })]))
    expect(out).toContain('Terkirim ke MISP')
    expect(out).not.toContain('border-gagal')
    expect(out).not.toMatch(NO_GREEN)
  })

  it('viewer juga melihat status kiriman (read-only)', () => {
    const out = panel(ready([makeIoc({ id: 1, check_id: 3, status: 'mock_sent' })]), VIEWER)
    expect(out).toContain('Terkirim (mock)')
    expect(out).not.toContain('<form')
  })

  it('pending: abu netral, petunjuk "hubungi admin", tanpa tombol kirim walau akun berizin', () => {
    const out = panel(ready([makeIoc({ id: 1, check_id: 3, status: 'pending', misp_event_uuid: null })]))
    expect(out).toContain('Sedang diproses (pending)')
    expect(out).toContain('Bila tertahan lama, hubungi admin.')
    expect(out).not.toContain('<form')
    expect(out).not.toContain('<button')
    expect(out).not.toContain('border-gagal')
    expect(out).not.toMatch(/perlu|bg-yellow|text-yellow/)
  })

  it('failed: chip berbingkai + ikon X + "Gagal" + error_message; form kirim ulang terisi alasan dan tag', () => {
    const failed = makeIoc({
      id: 1,
      check_id: 3,
      status: 'failed',
      misp_event_uuid: null,
      error_message: 'Gagal mengirim ke MISP (ConnectError)',
      reason: 'alasan lama yang akan dikirim ulang',
      tags: ['tlp:amber', 'ioc'],
    })
    const out = panel(ready([failed]))
    expect(out).toContain('border-gagal')
    expect(out).toContain('Gagal')
    expect(out).toContain('Gagal mengirim ke MISP (ConnectError)')
    expect(out).toContain('Kirim ulang')
    expect(out).toContain('>alasan lama yang akan dikirim ulang</textarea>')
    expect(out).toContain('value="tlp:amber, ioc"')
    expect(out).not.toContain('Terkirim')
  })

  it('failed untuk akun tanpa izin: status terlihat, tanpa form', () => {
    const failed = makeIoc({ id: 1, check_id: 3, status: 'failed', misp_event_uuid: null, error_message: 'x' })
    const out = panel(ready([failed]), VIEWER)
    expect(out).toContain('Gagal')
    expect(out).not.toContain('<form')
  })

  it('mengirim: hanya check yang sedang dikirim yang menampilkan "Mengirim…"', () => {
    const mine = panel(ready([], { sendingIds: [3] }))
    expect(mine).toContain('Mengirim…')
    const other = panel(ready([], { sendingIds: [99] }))
    expect(other).not.toContain('Mengirim…')
  })

  it('keterangan info (409 di luar 100 terbaru) tampil netral tanpa form bila akun tak berhak', () => {
    const out = panel(ready([], { issues: { 3: { kind: 'info', message: 'Sudah dikirim (kiriman #8).' } } }), VIEWER)
    expect(out).toContain('Sudah dikirim (kiriman #8).')
    expect(out).not.toContain('border-gagal')
  })

  it('data pihak ketiga/isian dirender sebagai teks (HTML di-escape)', () => {
    const evil = makeIoc({
      id: 1,
      check_id: 3,
      reason: '<script>alert(1)</script> <img src=x onerror=alert(1)>',
      tags: ['<b>tag</b>'],
      error_message: null,
    })
    const out = html(<SubmissionView submission={evil} />)
    expect(out).not.toContain('<script>')
    expect(out).not.toContain('<img')
    expect(out).not.toContain('<b>')
    expect(out).toContain('&lt;script&gt;')
  })

  it('tidak ada tanda persen dan tidak ada hijau di semua keadaan', () => {
    for (const status of ['pending', 'mock_sent', 'sent', 'failed'] as const) {
      const out = panel(ready([makeIoc({ id: 1, check_id: 3, status })]))
      expect(out).not.toMatch(NO_PERCENT)
      expect(out).not.toMatch(NO_GREEN)
    }
  })
})

describe('MispView: tabel Kiriman MISP', () => {
  const view = (
    items: IocOut[],
    over: Partial<Pick<MispState, 'total' | 'status' | 'error' | 'loadingMore'>> = {},
  ) =>
    html(
      <MispView
        state={{ items, total: items.length, status: 'ready', error: null, loadingMore: false, ...over }}
        onLoadMore={noop}
        onRefresh={noop}
        onOpenCheck={noop}
      />,
    )

  it('kolom, IP monospace, uuid monospace, pengirim, waktu WIB', () => {
    const out = view([makeIoc({ id: 1, check_id: 3, ip: '118.25.6.39' })])
    for (const heading of ['Waktu', 'IP', 'Status', 'Event UUID', 'Pengirim', 'Alasan', 'Keterangan']) {
      expect(out).toContain(`>${heading}</th>`)
    }
    expect(out).toContain('<span class="font-mono">118.25.6.39</span>')
    expect(out).toMatch(/<code class="font-mono[^"]*">MOCK-/)
    expect(out).toContain('analis_misp')
    expect(out).toContain('03 Nov 2026 10:00:00 WIB')
    expect(out).toContain('Buka check #3')
  })

  it('tabel dibungkus area gulir yang bisa difokus (7 kolom tidak muat di 1024px)', () => {
    const out = view([makeIoc({ id: 1 })])
    expect(out).toContain('overflow-x-auto')
    expect(out).toContain('role="region"')
    expect(out).toContain('tabindex="0"')
  })

  it('mock_sent tidak pernah "Terkirim ke MISP"; failed merah dengan error_message; pending dengan petunjuk', () => {
    const out = view([
      makeIoc({ id: 3, status: 'failed', misp_event_uuid: null, error_message: 'MISP_MODE=live belum diimplementasikan' }),
      makeIoc({ id: 2, status: 'pending', misp_event_uuid: null }),
      makeIoc({ id: 1, status: 'mock_sent' }),
    ])
    expect(out).toContain('Terkirim (mock)')
    expect(out).not.toContain('Terkirim ke MISP')
    expect(out).toContain('border-gagal')
    expect(out).toContain('MISP_MODE=live belum diimplementasikan')
    expect(out).toContain('Bila tertahan lama, hubungi admin.')
    expect(out).toContain('Sedang diproses (pending)')
  })

  it('tanpa uuid: "—" (bukan kosong atau 0)', () => {
    const out = view([makeIoc({ id: 1, status: 'failed', misp_event_uuid: null, error_message: 'x' })])
    expect(out).toContain('—')
  })

  it('alasan panjang dipotong dengan tombol "Tampilkan semua"; tag tampil sebagai chip teks', () => {
    const out = view([makeIoc({ id: 1, reason: 'a'.repeat(300), tags: ['tlp:amber'] })])
    expect(out).toContain('Tampilkan semua')
    expect(out).toContain('aria-expanded="false"')
    expect(out).not.toContain('a'.repeat(300))
    expect(out).toContain('tlp:amber')
  })

  it('kosong, memuat, dan galat memuat', () => {
    expect(view([])).toContain('Belum ada kiriman ke MISP.')
    expect(view([], { status: 'loading' })).toContain('Memuat daftar kiriman…')
    const err = view([], { status: 'error', error: 'API tidak terjangkau.' })
    expect(err).toContain('role="alert"')
    expect(err).not.toContain('Belum ada kiriman ke MISP.')
  })

  it('"Muat lagi" hanya bila masih ada yang belum dimuat', () => {
    expect(view([makeIoc({ id: 1 })], { total: 1 })).not.toContain('Muat lagi')
    const more = view([makeIoc({ id: 1 })], { total: 5 })
    expect(more).toContain('Muat lagi')
    expect(more).toContain('1 dari 5 dimuat')
  })

  it('tanpa persen dan tanpa hijau; catatan mode mock ada', () => {
    const out = view([makeIoc({ id: 1 }), makeIoc({ id: 2, status: 'sent' })])
    expect(out).not.toMatch(NO_PERCENT)
    expect(out).not.toMatch(NO_GREEN)
    expect(out).toContain('Mode mock')
  })
})
