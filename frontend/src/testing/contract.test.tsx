import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { createApiClient } from '../api/client'
import { isCheckOut } from '../api/guards'
import type { CheckOut } from '../api/types'
import { DecisionRail } from '../components/DecisionRail'
import { AbuseTab, RawJsonTab, SummaryTab, VirusTotalTab } from '../components/SourceTabs'
import { SummaryStrip } from '../components/SummaryStrip'
import { buildCopyText, findSource, formatScore, isSimulated } from '../lib/format'
import { parseCheckError } from '../lib/errors'
import { createWorkbenchStore } from '../workbench/store'
import mockSamples from './backend-mock-samples.json'
import rejectedSamples from './backend-rejected-samples.json'

// UJI KONTRAK: berkas JSON di sini adalah keluaran ASLI kode backend (adapter mock + assess + skema CheckOut /
// CheckRejected), dihasilkan di kontainer `api` tanpa database dan tanpa jaringan. Data fiktif (mode mock).
// Cara membuat ulang ada di docs/tasks/TASK-03-progress.md. Bila skema backend berubah, uji ini yang pertama gagal.

const samples = mockSamples as unknown as CheckOut[]
const bySample = (ip: string) => {
  const found = samples.find((c) => c.ip === ip)
  if (!found) throw new Error(`sampel ${ip} tidak ada`)
  return found
}
const html = (node: React.ReactNode) => renderToStaticMarkup(node)
const noop = () => {}
const scoreOf = (markup: string) => /Skor gabungan: <\/span>([^<]*)</.exec(markup)?.[1] ?? null

describe('kontrak: CheckOut asli backend', () => {
  it('ketujuh IP demo diterima penjaga bentuk', () => {
    expect(samples).toHaveLength(7)
    for (const sample of samples) expect(isCheckOut(sample)).toBe(true)
  })

  it('setiap hasil mock berflag SUMBER_SIMULASI (CLAUDE.md) dan terbaca sebagai simulasi', () => {
    for (const sample of samples) {
      expect(sample.flags).toContain('SUMBER_SIMULASI')
      expect(isSimulated(sample)).toBe(true)
    }
  })

  it('waktu dari backend berformat +07:00', () => {
    for (const sample of samples) expect(sample.checked_at).toMatch(/\+07:00$/)
  })

  it('semua tab dan panel untuk semua sampel ter-render tanpa galat, tanpa tanda persen dan tanpa hijau', () => {
    for (const sample of samples) {
      const outputs = [
        html(<SummaryStrip check={sample} />),
        html(<SummaryTab check={sample} />),
        html(<AbuseTab source={findSource(sample, 'abuseipdb')} />),
        html(<VirusTotalTab source={findSource(sample, 'virustotal')} />),
        html(<RawJsonTab check={sample} />),
        html(<DecisionRail check={sample} canRun submitting={false} onRerun={noop} />),
      ]
      for (const out of outputs) {
        expect(out).not.toContain('%')
        expect(out).not.toMatch(/green|emerald|lime|teal/)
        expect(out).not.toMatch(/NaN|undefined|\[object/)
      }
      expect(buildCopyText(sample)).toContain(sample.ip)
    }
  })
})

describe('kontrak: hasil yang diminta "Cek selesai" Tahap 2 (tabel IP demo TASK-02)', () => {
  it('1.1.1.1: SANGAT_TINGGI', () => {
    const c = bySample('1.1.1.1')
    const out = html(<SummaryStrip check={c} />)
    expect(c.indication).toBe('SANGAT_TINGGI')
    expect(scoreOf(out)).toBe(formatScore(c.risk_score))
    expect(out).toContain('SANGAT_TINGGI')
    expect(out).toContain('bg-sangat-strip')
  })

  it('1.0.0.1: HASIL_BERBEDA', () => {
    const c = bySample('1.0.0.1')
    expect(c.flags).toContain('HASIL_BERBEDA')
    expect(html(<SummaryTab check={c} />)).toContain('Hasil berbeda.')
  })

  it('8.8.8.8: N/A, DATA_TERBATAS 1/2, VirusTotal ERROR TIMEOUT', () => {
    const c = bySample('8.8.8.8')
    expect(c.risk_score).toBeNull()
    const out = html(<SummaryStrip check={c} />)
    expect(scoreOf(out)).toBe('N/A')
    expect(out).toContain('DATA_TERBATAS')
    expect(out).toContain('1/2')
    expect(out).toContain('ERROR · TIMEOUT')
    expect(html(<SummaryTab check={c} />)).toContain('sumber gagal: sumber tidak menjawab tepat waktu')
  })

  it('8.8.4.4: N/A, TIDAK_TERSEDIA 0/2', () => {
    const c = bySample('8.8.4.4')
    const out = html(<SummaryStrip check={c} />)
    expect(scoreOf(out)).toBe('N/A')
    expect(out).toContain('TIDAK_TERSEDIA')
    expect(out).toContain('0/2')
    expect(out.match(/tidak menjawab/g)?.length).toBe(2)
  })

  it('9.9.9.9: WHITELISTED dengan skor tetap (tidak dipotong)', () => {
    const c = bySample('9.9.9.9')
    expect(c.flags).toContain('WHITELISTED')
    expect(c.risk_score).toBe(bySample('1.1.1.1').risk_score)
    expect(html(<DecisionRail check={c} canRun submitting={false} onRerun={noop} />)).toContain(
      'skor tidak dipotong',
    )
  })

  it('149.112.112.112: 0.0 + NO_VENDOR_OPINION, RENDAH tidak hijau', () => {
    const c = bySample('149.112.112.112')
    const out = html(<SummaryStrip check={c} />)
    expect(scoreOf(out)).toBe('0.0')
    expect(c.flags).toContain('NO_VENDOR_OPINION')
    expect(out).toContain('RENDAH')
    expect(out).toContain('bg-rendah-bg')
    expect(out).not.toMatch(/green|emerald|lime|teal/)
  })

  it('208.67.222.222: N/A, INSUFFICIENT_DATA, VirusTotal tanpa vendor yang menilai', () => {
    const c = bySample('208.67.222.222')
    const out = html(<SummaryStrip check={c} />)
    expect(scoreOf(out)).toBe('N/A')
    expect(out).toContain('INSUFFICIENT_DATA')
    const vt = html(<VirusTotalTab source={findSource(c, 'virustotal')} />)
    expect(vt).toContain('tidak ada vendor yang menilai')
  })

  it('mock tidak punya lastReportedAt: waktu laporan terakhir "tidak tersedia"', () => {
    const abuse = html(<AbuseTab source={findSource(bySample('1.1.1.1'), 'abuseipdb')} />)
    expect(abuse).toContain('Laporan terakhir')
    expect(abuse).toContain('tidak tersedia')
  })
})

describe('kontrak: input ditolak (badan 422 asli backend)', () => {
  const inputs = Object.entries(rejectedSamples)

  it('keempat input di "Cek selesai" ada', () => {
    expect(inputs.map(([raw]) => raw)).toEqual(['10.10.50.10', '127.0.0.1', '2001:db8::1', 'abc'])
  })

  it.each(inputs)('%s: parseCheckError membawa pesan dan reason_code backend', (_raw, body) => {
    const error = parseCheckError({ ok: false, status: 422, kind: 'http', body })
    expect(error).toEqual({
      kind: 'input_ditolak',
      message: body.message,
      reasonCode: body.reason_code,
    })
  })

  it.each(inputs)('%s: store menampilkan pesan, riwayat dan pilihan tidak berubah', async (raw, body) => {
    const api = createApiClient({
      getToken: () => 'tok',
      onUnauthorized: () => {},
      fetchImpl: ((_url: string, init: RequestInit) =>
        Promise.resolve(
          init.method === 'POST'
            ? new Response(JSON.stringify(body), { status: 422, headers: { 'Content-Type': 'application/json' } })
            : new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0 }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
              }),
        )) as unknown as typeof fetch,
    })
    const store = createWorkbenchStore(api)
    await store.loadInitial()
    expect(await store.submit(raw)).toBe(false)
    const state = store.getState()
    expect(state.submitError).toEqual({
      kind: 'input_ditolak',
      message: body.message,
      reasonCode: body.reason_code,
    })
    expect(state.history).toEqual([])
    expect(state.selected).toBeNull()
  })
})
