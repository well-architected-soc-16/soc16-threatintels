import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { CheckOut } from '../api/types'
import { DEMO_CHECKS, LEGACY_CHECK, makeCheck, makeSource } from '../testing/fixtures'
import type { WorkbenchState } from '../workbench/store'
import { DecisionRail } from './DecisionRail'
import { EvidencePanel } from './EvidencePanel'
import { HistoryRail } from './HistoryRail'
import { SearchBar } from './SearchBar'
import { AbuseTab, RawJsonTab, SummaryTab, VirusTotalTab } from './SourceTabs'
import { SummaryStrip } from './SummaryStrip'

// Render markup (tanpa peramban) untuk mengunci invarian Aturan tampilan pada fixture SINTETIS.
// Yang diuji adalah tampilan, bukan rumus skor backend.

const html = (node: React.ReactNode) => renderToStaticMarkup(node)
const noop = () => {}
const demo = (ip: keyof typeof DEMO_CHECKS) => DEMO_CHECKS[ip]

// Teks isi blok skor di strip (setelah label sr-only).
function scoreOf(markup: string): string | null {
  const match = /Skor gabungan: <\/span>([^<]*)</.exec(markup)
  return match ? match[1] : null
}

describe('SummaryStrip: tujuh IP demo TASK-02', () => {
  it('1.1.1.1: SANGAT_TINGGI, blok solid merah, badge simulasi', () => {
    const out = html(<SummaryStrip check={demo('1.1.1.1')} />)
    expect(scoreOf(out)).toBe('77.0')
    expect(out).toContain('SANGAT_TINGGI')
    expect(out).toContain('bg-sangat-strip')
    expect(out).toContain('Indikasi sangat tinggi · periksa segera, tanpa auto-block')
    expect(out).toContain('SIMULASI · bukan data nyata')
    expect(out).toContain('simulasi-frame')
    expect(out).toContain('1.1.1.1')
  })

  it('1.0.0.1: PERLU_PEMERIKSAAN dan peringatan HASIL_BERBEDA di tab Ringkasan', () => {
    const check = demo('1.0.0.1')
    expect(scoreOf(html(<SummaryStrip check={check} />))).toBe('49.1')
    expect(html(<SummaryStrip check={check} />)).toContain('PERLU_PEMERIKSAAN')
    const tab = html(<SummaryTab check={check} />)
    expect(tab).toContain('Hasil berbeda.')
    expect(tab).toContain('selisih ≥ 50')
  })

  it('8.8.8.8: skor N/A (bukan 0), DATA_TERBATAS 1/2, VirusTotal tidak menjawab karena TIMEOUT', () => {
    const out = html(<SummaryStrip check={demo('8.8.8.8')} />)
    expect(scoreOf(out)).toBe('N/A')
    expect(scoreOf(out)).not.toMatch(/^0/)
    expect(out).toContain('DATA_TERBATAS')
    expect(out).toContain('hanya satu sumber yang menjawab')
    expect(out).toContain('1/2')
    expect(out).toContain('VirusTotal</span> tidak menjawab')
    expect(out).toContain('ERROR · TIMEOUT')
    expect(out).toContain('border-dashed')
    expect(out).not.toContain('bg-sangat-strip')
  })

  it('8.8.4.4: N/A, TIDAK_TERSEDIA 0/2, kedua sumber tidak menjawab', () => {
    const out = html(<SummaryStrip check={demo('8.8.4.4')} />)
    expect(scoreOf(out)).toBe('N/A')
    expect(out).toContain('TIDAK_TERSEDIA')
    expect(out).toContain('0/2')
    expect(out.match(/tidak menjawab/g)?.length).toBe(2)
    expect(out).toContain('NO_RECORD')
  })

  it('9.9.9.9: WHITELISTED tampil di rel keputusan dan skor tidak dipotong', () => {
    const check = demo('9.9.9.9')
    expect(scoreOf(html(<SummaryStrip check={check} />))).toBe('77.0')
    const rail = html(<DecisionRail check={check} canRun submitting={false} onRerun={noop} />)
    expect(rail).toContain('WHITELISTED')
    expect(rail).toContain('skor tidak dipotong')
  })

  it('149.112.112.112: skor 0.0 + NO_VENDOR_OPINION, RENDAH abu-slate dan TIDAK hijau', () => {
    const check = demo('149.112.112.112')
    const out = html(<SummaryStrip check={check} />)
    expect(scoreOf(out)).toBe('0.0')
    expect(out).toContain('RENDAH')
    expect(out).toContain('bg-rendah-bg')
    expect(out).not.toMatch(/green|emerald|lime|teal/)
    expect(html(<DecisionRail check={check} canRun submitting={false} onRerun={noop} />)).toContain(
      'NO_VENDOR_OPINION',
    )
    expect(html(<SummaryTab check={check} />)).toContain('NO_VENDOR_OPINION')
    expect(html(<SummaryStrip check={check} />)).toContain('Indikasi rendah · tetap baca bukti')
  })

  it('208.67.222.222: N/A, DATA_TERBATAS, VirusTotal INSUFFICIENT_DATA tanpa vendor yang menilai', () => {
    const check = demo('208.67.222.222')
    const out = html(<SummaryStrip check={check} />)
    expect(scoreOf(out)).toBe('N/A')
    expect(out).toContain('INSUFFICIENT_DATA')
    const vt = html(<VirusTotalTab source={check.sources[1]} />)
    expect(vt).toContain('INSUFFICIENT_DATA')
    expect(vt).toContain('tidak ada vendor yang menilai')
    expect(vt).not.toMatch(/NaN|0 \/ 0/)
  })

  it('semua IP demo: tanpa tanda persen, tanpa warna hijau, dan skor tidak pernah "0" bila null', () => {
    for (const check of Object.values(DEMO_CHECKS)) {
      const out = html(<SummaryStrip check={check} />)
      expect(out).not.toContain('%')
      expect(out).not.toMatch(/green|emerald|lime|teal/)
      expect(out).toContain('SIMULASI · bukan data nyata')
      if (check.risk_score === null) expect(scoreOf(out)).toBe('N/A')
    }
  })
})

describe('check lama TASK-01', () => {
  it('tidak berlabel "Ambil baru"/"Cache"; waktu dan HTTP tampil "tidak tersedia", tanpa crash', () => {
    const tab = html(<SummaryTab check={LEGACY_CHECK} />)
    expect(tab).not.toContain('Ambil baru')
    expect(tab).not.toContain('Cache')
    const abuse = html(<AbuseTab source={LEGACY_CHECK.sources[0]} />)
    expect(abuse).toContain('Tidak ada bukti dari sumber ini.')
    expect(abuse).toContain('tidak tersedia')
    expect(abuse).not.toContain('Ambil baru')
    expect(abuse).toContain('ADAPTER_NOT_IMPLEMENTED')
  })

  it('tanpa badge simulasi dan label N/A', () => {
    const out = html(<SummaryStrip check={LEGACY_CHECK} />)
    expect(out).not.toContain('SIMULASI')
    expect(scoreOf(out)).toBe('N/A')
  })
})

describe('tab AbuseIPDB dan VirusTotal', () => {
  it('AbuseIPDB: field bukti, tanpa key simulasi; mock tanpa source_time = "tidak tersedia"', () => {
    const out = html(<AbuseTab source={demo('1.1.1.1').sources[0]} />)
    for (const key of ['abuseConfidenceScore', 'totalReports', 'numDistinctUsers', 'isWhitelisted']) {
      expect(out).toContain(key)
    }
    expect(out).not.toContain('simulasi')
    expect(out).toContain('Laporan terakhir')
    expect(out).toContain('tidak tersedia')
  })

  it('AbuseIPDB: waktu dari source_time (WIB); lastReportedAt UTC mentah di evidence TIDAK dirender', () => {
    const source = makeSource({
      source: 'abuseipdb',
      status: 'OK_SIGNAL',
      normalized_score: 90,
      source_time: '2026-11-02T14:00:00+07:00',
      source_time_type: 'last_report',
      evidence_summary: {
        abuseConfidenceScore: 90,
        totalReports: 3,
        numDistinctUsers: 2,
        lastReportedAt: '2026-11-02T07:00:00+00:00',
        isWhitelisted: null,
      },
    })
    const out = html(<AbuseTab source={source} />)
    expect(out).toContain('02 Nov 2026 14:00:00 WIB')
    expect(out).not.toContain('+00:00')
    expect(out).toContain('tidak diketahui')
  })

  it('VirusTotal: key yang hilang tampil "—" (bukan 0) disertai catatan rasio', () => {
    const source = makeSource({
      source: 'virustotal',
      status: 'OK_SIGNAL',
      evidence_summary: { malicious: 3, harmless: 7 },
    })
    const out = html(<VirusTotalTab source={source} />)
    expect(out).toContain('3 / 10 vendor (sebagian kategori tidak ada di respons sumber)')
    expect(out.match(/>—</g)?.length).toBe(3)
    expect(out).not.toContain('%')
  })

  it('nilai bukti bertipe salah (data pihak ketiga) tidak membuat crash dan tampil "—"', () => {
    const source = makeSource({
      source: 'virustotal',
      status: 'OK_SIGNAL',
      evidence_summary: { malicious: 'banyak', suspicious: null, harmless: {}, undetected: [], timeout: Infinity },
    })
    expect(() => html(<VirusTotalTab source={source} />)).not.toThrow()
    expect(html(<VirusTotalTab source={source} />)).toContain('Tidak ada bukti dari sumber ini.')
  })

  it('sumber tidak ada pada pemeriksaan: pesan, bukan crash', () => {
    expect(html(<AbuseTab source={undefined} />)).toContain('tidak ada pada pemeriksaan ini')
    expect(html(<VirusTotalTab source={undefined} />)).toContain('tidak ada pada pemeriksaan ini')
  })

  it('RATE_LIMIT menampilkan "coba lagi ±N detik" di Ringkasan', () => {
    const check = makeCheck({
      ip: '1.1.1.1',
      sources: [
        makeSource({
          source: 'virustotal',
          status: 'ERROR',
          reason: 'RATE_LIMIT',
          retry_after_seconds: 42,
          flags: [],
        }),
      ],
    })
    expect(html(<SummaryTab check={check} />)).toContain('coba lagi ±42 detik')
  })

  it('Raw JSON: teks apa adanya', () => {
    const out = html(<RawJsonTab check={demo('1.1.1.1')} />)
    expect(out).toContain('<pre')
    expect(out).toContain('&quot;ip&quot;: &quot;1.1.1.1&quot;')
  })
})

describe('data pihak ketiga dirender sebagai teks (Aturan tampilan 7)', () => {
  const evil = makeCheck({
    id: 666,
    ip: '<img src=x onerror=alert(1)>',
    checked_by: '<script>alert(1)</script>',
    flags: [],
    sources: [
      makeSource({
        source: '<b>sumber</b>',
        status: 'ERROR',
        reason: '<i>x</i>' as never,
        flags: [],
        evidence_summary: { malicious: '<svg onload=alert(1)>' },
      }),
    ],
  })

  it('markup berbahaya di ip, checked_by, nama sumber, dan reason keluar sebagai teks ter-escape', () => {
    const outputs = [
      html(<SummaryStrip check={evil} />),
      html(<SummaryTab check={evil} />),
      html(<DecisionRail check={evil} canRun submitting={false} onRerun={noop} />),
      html(<RawJsonTab check={evil} />),
      html(
        <HistoryRail
          state={baseState({ history: [evil], total: 1, historyStatus: 'ready' })}
          onSelect={noop}
          onLoadMore={noop}
          onRetry={noop}
        />,
      ),
    ]
    for (const out of outputs) {
      expect(out).not.toMatch(/<img/i)
      expect(out).not.toMatch(/<script/i)
      expect(out).not.toMatch(/<svg onload/i)
      expect(out).not.toMatch(/<b>sumber/i)
    }
    expect(outputs[0]).toContain('&lt;img src=x onerror=alert(1)&gt;')
  })

  it('IP non-IPv4 tidak menghasilkan tautan pivot', () => {
    const out = html(<DecisionRail check={evil} canRun submitting={false} onRerun={noop} />)
    expect(out).not.toContain('abuseipdb.com')
    expect(out).not.toContain('virustotal.com')
  })
})

function baseState(over: Partial<WorkbenchState> = {}): WorkbenchState {
  return {
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
    ...over,
  }
}

describe('HistoryRail', () => {
  const rail = (over: Partial<WorkbenchState>) =>
    html(
      <HistoryRail
        state={baseState({ historyStatus: 'ready', ...over })}
        onSelect={noop}
        onLoadMore={noop}
        onRetry={noop}
      />,
    )

  it('baris menampilkan IP, label dari indication, skor/N/A, waktu, dan badge simulasi', () => {
    const history = Object.values(DEMO_CHECKS)
    const out = rail({ history, total: history.length })
    for (const check of history) expect(out).toContain(check.ip)
    expect(out.match(/SIMULASI · bukan data nyata/g)?.length).toBe(history.length)
    expect(out).toContain('SANGAT_TINGGI')
    expect(out).toContain('N/A')
    expect(out).toContain('03 Nov 2026 10:00:00 WIB')
    expect(out).not.toContain('%')
  })

  it('label HANYA dari indication: skor tinggi dengan indication null tetap N/A', () => {
    const odd = makeCheck({ id: 5, ip: '1.2.3.4', risk_score: 99, indication: null })
    const out = rail({ history: [odd], total: 1 })
    expect(out).toContain('N/A')
    expect(out).not.toContain('SANGAT_TINGGI')
  })

  it('"Muat lagi" tampil bila belum semua dimuat dan hilang bila sudah', () => {
    const history = [demo('1.1.1.1'), demo('8.8.8.8')]
    expect(rail({ history, total: 5 })).toContain('Muat lagi')
    expect(rail({ history, total: 5 })).toContain('2 dari 5 dimuat')
    expect(rail({ history, total: 2 })).not.toContain('Muat lagi')
  })

  it('catatan penyaringan menyebut "yang sudah dimuat"', () => {
    expect(rail({ history: [demo('1.1.1.1')], total: 1 })).toContain('Menyaring yang sudah dimuat')
  })

  it('keadaan memuat, kosong, dan galat', () => {
    expect(rail({ historyStatus: 'loading' })).toContain('Memuat riwayat…')
    expect(rail({ history: [], total: 0 })).toContain('Belum ada pemeriksaan.')
    const failed = rail({ historyStatus: 'error', historyError: 'Riwayat gagal dimuat (HTTP 500).' })
    expect(failed).toContain('role="alert"')
    expect(failed).toContain('Coba lagi')
  })

  it('baris terpilih bertanda aria-current', () => {
    const history = [demo('1.1.1.1'), demo('8.8.8.8')]
    const out = rail({ history, total: 2, selected: history[0] })
    expect(out.match(/aria-current="true"/g)?.length).toBe(1)
  })
})

describe('DecisionRail: RBAC tampilan dan aksi', () => {
  const rail = (check: CheckOut | null, canRun: boolean, submitting = false) =>
    html(<DecisionRail check={check} canRun={canRun} submitting={submitting} onRerun={noop} />)

  it('viewer tidak melihat Cek ulang tetapi tetap bisa Salin hasil dan membaca detail', () => {
    const out = rail(demo('1.1.1.1'), false)
    expect(out).not.toContain('Cek ulang')
    expect(out).toContain('Salin hasil')
    expect(out).toContain('Cakupan')
  })

  it('analyst/admin melihat Cek ulang; nonaktif saat memeriksa', () => {
    expect(rail(demo('1.1.1.1'), true)).toContain('Cek ulang')
    const busy = rail(demo('1.1.1.1'), true, true)
    expect(busy).toContain('Memeriksa…')
    expect(busy).toMatch(/<button[^>]*disabled[^>]*>Memeriksa…/)
  })

  it('hasil simulasi: teks pengganti, tanpa tombol kirim MISP (Aturan tampilan 4)', () => {
    const out = rail(demo('1.1.1.1'), true)
    expect(out).toContain('Hasil simulasi tidak boleh dikirim ke MISP.')
    expect(out).not.toContain('Kirim ke MISP')
  })

  it('bukan simulasi: tidak memajang teks larangan simulasi', () => {
    expect(rail(LEGACY_CHECK, true)).not.toContain('Hasil simulasi tidak boleh')
  })

  it('tautan pivot membuka tab baru dengan rel aman', () => {
    const out = rail(demo('1.1.1.1'), true)
    expect(out).toContain('href="https://www.abuseipdb.com/check/1.1.1.1"')
    expect(out).toContain('href="https://www.virustotal.com/gui/ip-address/1.1.1.1"')
    expect(out.match(/target="_blank"/g)?.length).toBe(2)
    expect(out.match(/rel="noopener noreferrer"/g)?.length).toBe(2)
  })

  it('sumber yang tidak menjawab disebut di Cakupan; tanpa flag = "Tidak ada flag."', () => {
    const out = rail(demo('8.8.8.8'), true)
    expect(out).toContain('VirusTotal</span> tidak menjawab')
    expect(rail(LEGACY_CHECK, true)).toContain('Tidak ada flag.')
  })

  it('kesegaran: cache dengan masa berlaku, ambil baru, dan check lama tanpa label', () => {
    const cached = makeCheck({
      ip: '1.1.1.1',
      sources: [makeSource({ source: 'abuseipdb', status: 'OK_SIGNAL', from_cache: true, flags: [] })],
    })
    expect(rail(cached, true)).toContain('Cache, berlaku sampai 03 Nov 2026 16:00:00 WIB')
    expect(rail(demo('1.1.1.1'), true)).toContain('Ambil baru')
    expect(rail(LEGACY_CHECK, true)).not.toContain('Ambil baru')
  })

  it('belum ada hasil: hanya petunjuk', () => {
    const out = rail(null, true)
    expect(out).toContain('Aksi muncul setelah ada hasil pengecekan.')
    expect(out).not.toContain('Cek ulang')
  })
})

describe('SearchBar', () => {
  const bar = (over: { submitting?: boolean; error?: Parameters<typeof SearchBar>[0]['error'] } = {}) =>
    html(
      <SearchBar
        submitting={over.submitting ?? false}
        error={over.error ?? null}
        onSubmit={() => Promise.resolve(false)}
        onEdit={noop}
      />,
    )

  it('form method=post, label, placeholder, dan teks bantuan satu IPv4 publik', () => {
    const out = bar()
    expect(out).toMatch(/<form[^>]*method="post"/)
    expect(out).toContain('role="search"')
    expect(out).toContain('Alamat IPv4 publik')
    expect(out).toContain('IPv4 publik, mis. 118.25.6.39')
    expect(out).toContain('Satu IPv4 publik saja')
    expect(out).toContain('>Cek IP<')
  })

  it('memeriksa: tombol "Memeriksa…" nonaktif dan teks bisa sampai belasan detik', () => {
    const out = bar({ submitting: true })
    expect(out).toMatch(/<button[^>]*disabled[^>]*>Memeriksa…/)
    expect(out).toContain('bisa sampai belasan detik')
  })

  it('INPUT_DITOLAK: pesan backend dan reason_code di bawah kolom pencarian', () => {
    const out = bar({
      error: { kind: 'input_ditolak', message: 'Alamat privat/internal tidak diperiksa', reasonCode: 'PRIVATE' },
    })
    expect(out).toContain('role="alert"')
    expect(out).toContain('Alamat privat/internal tidak diperiksa')
    expect(out).toContain('PRIVATE')
  })

  it('galat biasa menampilkan pesan tanpa reason_code', () => {
    const out = bar({ error: { kind: 'message', message: 'Masukkan alamat IPv4 publik.' } })
    expect(out).toContain('Masukkan alamat IPv4 publik.')
  })
})

describe('EvidencePanel', () => {
  const panel = (over: Partial<Parameters<typeof EvidencePanel>[0]> = {}) =>
    html(
      <EvidencePanel
        selected={null}
        detailLoading={false}
        detailError={null}
        submitting={false}
        canRun
        {...over}
      />,
    )

  it('keadaan awal: satu kalimat petunjuk, berbeda untuk viewer', () => {
    expect(panel()).toContain('Masukkan IPv4 publik di kolom pencarian')
    expect(panel({ canRun: false })).toContain('Pilih pemeriksaan dari riwayat.')
    expect(panel({ canRun: false })).not.toContain('kolom pencarian')
  })

  it('satu loading state dengan teks bisa sampai belasan detik', () => {
    const out = panel({ submitting: true })
    expect(out).toContain('role="status"')
    expect(out).toContain('bisa sampai belasan detik')
    expect(out).toContain('bar-indeterminate')
  })

  it('check terpilih: strip, empat tab, dan panel tab Ringkasan; tepat satu h1', () => {
    const out = panel({ selected: demo('1.1.1.1') })
    for (const label of ['Ringkasan', 'AbuseIPDB', 'VirusTotal', 'Raw JSON']) expect(out).toContain(label)
    expect(out).toContain('role="tablist"')
    expect(out).toContain('role="tabpanel"')
    expect(out.match(/aria-selected="true"/g)?.length).toBe(1)
    expect(out.match(/<h1/g)?.length).toBe(1)
    expect(out).toContain('SANGAT_TINGGI')
  })

  it('galat detail tampil sebagai peringatan merah berikon dan teks', () => {
    const out = panel({ detailError: 'Pemeriksaan tidak ditemukan.' })
    expect(out).toContain('role="alert"')
    expect(out).toContain('Pemeriksaan tidak ditemukan.')
  })
})
