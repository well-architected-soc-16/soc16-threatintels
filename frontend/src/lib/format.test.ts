import { describe, expect, it } from 'vitest'
import type { SourceResult } from '../api/types'
import { DEMO_CHECKS, LEGACY_CHECK, makeSource } from '../testing/fixtures'
import {
  assessmentText,
  buildCopyText,
  cacheLabel,
  contributes,
  describeSource,
  describeVendorRatio,
  evidenceBool,
  evidenceNumber,
  findSource,
  flagText,
  formatCount,
  formatNormalizedScore,
  formatScore,
  formatTime,
  indicationView,
  isSimulated,
  pivotLinks,
  reasonText,
  silentSources,
  sourceName,
  sourceTimeLabel,
  vendorRatio,
  whitelistText,
} from './format'

describe('formatScore / formatNormalizedScore', () => {
  it('null menjadi N/A, BUKAN 0 (Aturan tampilan 1)', () => {
    expect(formatScore(null)).toBe('N/A')
    expect(formatScore(undefined)).toBe('N/A')
    expect(formatScore(Number.NaN)).toBe('N/A')
    expect(formatScore(null)).not.toBe('0')
    expect(formatScore(null)).not.toBe('0.0')
  })

  it('skor nyata satu desimal dengan titik; nol sungguhan tetap 0.0', () => {
    expect(formatScore(3.8)).toBe('3.8')
    expect(formatScore(0)).toBe('0.0')
    expect(formatScore(75)).toBe('75.0')
    expect(formatScore(92.4)).toBe('92.4')
  })

  it('tidak pernah memakai tanda persen (Aturan tampilan 2)', () => {
    for (const value of [null, 0, 3.8, 75, 100]) {
      expect(formatScore(value)).not.toContain('%')
    }
  })

  it('skor sumber null menjadi "—", bukan 0', () => {
    expect(formatNormalizedScore(null)).toBe('—')
    expect(formatNormalizedScore(0)).toBe('0')
    expect(formatNormalizedScore(90)).toBe('90')
  })
})

describe('indicationView', () => {
  it.each([
    ['RENDAH', 'rendah', 'Indikasi rendah · tetap baca bukti'],
    ['PERLU_PEMERIKSAAN', 'perlu', 'Perlu pemeriksaan'],
    ['TINGGI', 'tinggi', 'Indikasi tinggi · dahulukan pemeriksaan'],
    [
      'SANGAT_TINGGI',
      'sangat',
      'Indikasi sangat tinggi · periksa segera, tanpa auto-block',
    ],
  ] as const)('%s', (indication, tone, text) => {
    expect(indicationView(indication)).toEqual({ tone, code: indication, text })
  })

  it('null = N/A abu-abu (bukan label apa pun)', () => {
    expect(indicationView(null)).toEqual({ tone: 'na', code: 'N/A', text: 'N/A' })
  })

  it('nilai tak dikenal tampil sebagai kode aslinya, netral, dan tidak menarik properti prototipe', () => {
    expect(indicationView('ANEH' as never)).toEqual({ tone: 'na', code: 'ANEH', text: 'ANEH' })
    expect(indicationView('constructor' as never).tone).toBe('na')
    expect(indicationView('__proto__' as never).tone).toBe('na')
  })

  it('RENDAH tidak pernah bernada hijau atau aman', () => {
    const text = indicationView('RENDAH').text.toLowerCase()
    expect(text).not.toContain('aman')
    expect(text).toContain('tetap baca bukti')
  })
})

describe('status sumber, reason, dan flag', () => {
  const src = (over: Partial<SourceResult>): SourceResult =>
    makeSource({ source: 'abuseipdb', status: 'ERROR', ...over })

  it('menjelaskan keenam status', () => {
    expect(describeSource(src({ status: 'OK_SIGNAL' }))).toBe('ada sinyal buruk')
    expect(describeSource(src({ status: 'OK_NO_SIGNAL' }))).toContain('bukan jaminan aman')
    expect(describeSource(src({ status: 'NO_RECORD' }))).toContain('tidak punya catatan')
    expect(describeSource(src({ status: 'INSUFFICIENT_DATA' }))).toContain('tidak cukup')
    expect(describeSource(src({ status: 'ERROR', reason: 'TIMEOUT' }))).toBe(
      'sumber gagal: sumber tidak menjawab tepat waktu',
    )
    expect(describeSource(src({ status: 'SKIPPED', reason: 'QUOTA_INTERNAL' }))).toBe(
      'dilewati: kuota internal tool ini habis',
    )
  })

  it('setiap reason yang dikenal punya teks Indonesia', () => {
    for (const reason of [
      'AUTH', 'RATE_LIMIT', 'TIMEOUT', 'UPSTREAM', 'INVALID_RESPONSE',
      'INTERNAL_ERROR', 'ADAPTER_NOT_IMPLEMENTED', 'QUOTA_INTERNAL',
    ]) {
      expect(reasonText(reason)).not.toBe('alasan tidak dikenal')
      expect(reasonText(reason)).not.toBe(reason)
    }
  })

  it('reason kosong atau tak dikenal tidak menimbulkan galat', () => {
    expect(reasonText(null)).toBe('alasan tidak dicatat')
    expect(reasonText('')).toBe('alasan tidak dicatat')
    expect(reasonText('BARU_DARI_BACKEND')).toBe('alasan tidak dikenal')
    expect(reasonText('constructor')).toBe('alasan tidak dikenal')
  })

  it('RATE_LIMIT dengan retry_after_seconds menambah "coba lagi ±N detik"', () => {
    expect(
      describeSource(src({ reason: 'RATE_LIMIT', retry_after_seconds: 30 })),
    ).toBe('sumber gagal: kuota atau batas laju sumber tercapai; coba lagi ±30 detik')
    expect(describeSource(src({ reason: 'RATE_LIMIT', retry_after_seconds: null }))).not.toContain('coba lagi')
    expect(describeSource(src({ reason: 'RATE_LIMIT', retry_after_seconds: 0 }))).not.toContain('coba lagi')
    // retry hanya untuk RATE_LIMIT
    expect(describeSource(src({ reason: 'TIMEOUT', retry_after_seconds: 30 }))).not.toContain('coba lagi')
  })

  it('status tak dikenal tidak crash', () => {
    expect(describeSource(src({ status: 'BARU' as never }))).toBe('status sumber tidak dikenal')
  })

  it('hanya OK_SIGNAL dan OK_NO_SIGNAL yang menambah cakupan', () => {
    expect(contributes('OK_SIGNAL')).toBe(true)
    expect(contributes('OK_NO_SIGNAL')).toBe(true)
    for (const status of ['NO_RECORD', 'INSUFFICIENT_DATA', 'ERROR', 'SKIPPED']) {
      expect(contributes(status)).toBe(false)
    }
  })

  it('silentSources memilih yang tidak menjawab', () => {
    const silent = silentSources(DEMO_CHECKS['8.8.8.8']).map((s) => s.source)
    expect(silent).toEqual(['virustotal'])
    expect(silentSources(DEMO_CHECKS['8.8.4.4'])).toHaveLength(2)
    expect(silentSources(DEMO_CHECKS['1.1.1.1'])).toHaveLength(0)
  })

  it('teks flag dan nama sumber punya cadangan kode asli', () => {
    expect(flagText('HASIL_BERBEDA')).toContain('selisih ≥ 50')
    expect(flagText('WHITELISTED')).toContain('skor tidak dipotong')
    expect(flagText('NO_VENDOR_OPINION')).toContain('tidak memberi opini')
    expect(flagText('BARU')).toBe('flag tidak dikenal')
    expect(flagText('constructor')).toBe('flag tidak dikenal')
    expect(sourceName('abuseipdb')).toBe('AbuseIPDB')
    expect(sourceName('virustotal')).toBe('VirusTotal')
    expect(sourceName('shodan')).toBe('shodan')
    expect(sourceName('constructor')).toBe('constructor')
  })

  it('teks jenis waktu sumber', () => {
    expect(sourceTimeLabel('last_report')).toBe('laporan terakhir')
    expect(sourceTimeLabel('last_analysis')).toBe('analisis terakhir')
    expect(sourceTimeLabel(null)).toBe('tidak tersedia')
    expect(sourceTimeLabel('lain')).toBe('tidak tersedia')
  })

  it('penjelasan status penilaian', () => {
    expect(assessmentText('DATA_TERBATAS')).toContain('satu sumber')
    expect(assessmentText('TIDAK_TERSEDIA')).toContain('tidak ada sumber')
    expect(assessmentText('BARU')).toBe('status penilaian tidak dikenal')
  })
})

describe('cacheLabel', () => {
  it('Cache / Ambil baru hanya bila retrieved_at ada', () => {
    expect(cacheLabel({ retrieved_at: '2026-11-03T10:00:00+07:00', from_cache: true })).toBe('Cache')
    expect(cacheLabel({ retrieved_at: '2026-11-03T10:00:00+07:00', from_cache: false })).toBe('Ambil baru')
  })

  it('check lama TASK-01 (retrieved_at null, from_cache false) TIDAK berlabel "Ambil baru"', () => {
    expect(cacheLabel({ retrieved_at: null, from_cache: false })).toBeNull()
    for (const source of LEGACY_CHECK.sources) expect(cacheLabel(source)).toBeNull()
  })
})

describe('formatTime', () => {
  it('+07:00 menjadi format WIB tanpa new Date()', () => {
    expect(formatTime('2026-11-02T14:03:07+07:00')).toBe('02 Nov 2026 14:03:07 WIB')
    expect(formatTime('2026-05-09T00:00:00+07:00')).toBe('09 Mei 2026 00:00:00 WIB')
    expect(formatTime('2026-08-17T23:59:59+07:00')).toBe('17 Agu 2026 23:59:59 WIB')
  })

  it('+00:00 (UTC mentah milik evidence) TIDAK dilabeli WIB dan tidak dikonversi', () => {
    const utc = '2026-11-02T07:03:07+00:00'
    expect(formatTime(utc)).toBe(utc)
    expect(formatTime(utc)).not.toContain('WIB')
    expect(formatTime('2026-11-02T07:03:07Z')).toBe('2026-11-02T07:03:07Z')
    expect(formatTime('2026-11-02T14:03:07+08:00')).toBe('2026-11-02T14:03:07+08:00')
  })

  it('string yang tidak cocok pola tampil mentah', () => {
    expect(formatTime('kemarin')).toBe('kemarin')
    expect(formatTime('2026-13-02T14:03:07+07:00')).toBe('2026-13-02T14:03:07+07:00')
    expect(formatTime('2026-11-02T25:03:07+07:00')).toBe('2026-11-02T25:03:07+07:00')
    expect(formatTime('2026-11-02T14:61:07+07:00')).toBe('2026-11-02T14:61:07+07:00')
  })

  it('pecahan detik diterima dan dibuang; null atau bukan teks = tidak tersedia', () => {
    expect(formatTime('2026-11-02T14:03:07.123456+07:00')).toBe('02 Nov 2026 14:03:07 WIB')
    expect(formatTime(null)).toBe('tidak tersedia')
    expect(formatTime(undefined)).toBe('tidak tersedia')
    expect(formatTime(12345 as never)).toBe('tidak tersedia')
  })
})

describe('bukti sumber (data pihak ketiga dibaca defensif)', () => {
  it('evidenceNumber hanya menerima angka hingga; selain itu null', () => {
    const ev = { a: 5, b: '5', c: null, d: Number.NaN, e: Infinity, f: {} }
    expect(evidenceNumber(ev, 'a')).toBe(5)
    for (const key of ['b', 'c', 'd', 'e', 'f', 'tidak-ada', 'constructor', '__proto__']) {
      expect(evidenceNumber(ev, key)).toBeNull()
    }
    expect(evidenceNumber(null, 'a')).toBeNull()
    expect(evidenceNumber(undefined, 'a')).toBeNull()
  })

  it('evidenceBool dan teks whitelist: null = tidak diketahui', () => {
    expect(evidenceBool({ x: true }, 'x')).toBe(true)
    expect(evidenceBool({ x: false }, 'x')).toBe(false)
    expect(evidenceBool({ x: 'true' }, 'x')).toBeNull()
    expect(evidenceBool({}, 'x')).toBeNull()
    expect(whitelistText(null)).toBe('tidak diketahui')
    expect(whitelistText(true)).toBe('ya')
    expect(whitelistText(false)).toBe('tidak')
  })

  it('formatCount: kunci hilang menjadi "—", bukan 0', () => {
    expect(formatCount(null)).toBe('—')
    expect(formatCount(0)).toBe('0')
    expect(formatCount(12)).toBe('12')
  })

  it('rasio vendor: lengkap, tanpa persen', () => {
    const ratio = vendorRatio({ malicious: 10, suspicious: 2, harmless: 50, undetected: 30 })
    expect(ratio).toEqual({ flagged: 12, total: 92, missing: [] })
    expect(describeVendorRatio(ratio)).toBe('12 / 92 vendor')
    expect(describeVendorRatio(ratio)).not.toContain('%')
  })

  it('rasio vendor: key yang hilang dicatat, bukan dianggap 0', () => {
    const ratio = vendorRatio({ malicious: 3, harmless: 7 })
    expect(ratio?.missing).toEqual(['suspicious', 'undetected'])
    expect(ratio).toMatchObject({ flagged: 3, total: 10 })
    expect(describeVendorRatio(ratio)).toBe(
      '3 / 10 vendor (sebagian kategori tidak ada di respons sumber)',
    )
  })

  it('rasio vendor: penyebut 0 (semua vendor timeout) tidak pernah menjadi 0/0 atau NaN', () => {
    const ratio = vendorRatio({ malicious: 0, suspicious: 0, harmless: 0, undetected: 0, timeout: 90 })
    expect(describeVendorRatio(ratio)).toBe('tidak ada vendor yang menilai')
    expect(describeVendorRatio(ratio)).not.toMatch(/NaN|0 \/ 0/)
  })

  it('rasio vendor: tanpa satu pun key = "—"', () => {
    expect(vendorRatio({})).toBeNull()
    expect(describeVendorRatio(vendorRatio({ simulasi: true }))).toBe('—')
    expect(vendorRatio({ malicious: 'banyak' })).toBeNull()
  })
})

describe('isSimulated', () => {
  it('membaca flag tingkat-check maupun flag sumber', () => {
    expect(isSimulated(DEMO_CHECKS['1.1.1.1'])).toBe(true)
    expect(isSimulated({ flags: [], sources: [makeSource({ source: 'abuseipdb', status: 'OK_SIGNAL' })] })).toBe(true)
    expect(isSimulated(LEGACY_CHECK)).toBe(false)
    expect(isSimulated({ flags: [], sources: [] })).toBe(false)
  })

  it('semua tujuh IP demo mock berstatus simulasi', () => {
    for (const check of Object.values(DEMO_CHECKS)) expect(isSimulated(check)).toBe(true)
  })
})

describe('findSource', () => {
  it('mencari sumber menurut nama', () => {
    expect(findSource(DEMO_CHECKS['1.1.1.1'], 'abuseipdb')?.source).toBe('abuseipdb')
    expect(findSource(DEMO_CHECKS['1.1.1.1'], 'shodan')).toBeUndefined()
  })
})

describe('buildCopyText', () => {
  it('memuat IP, waktu, status, skor, cakupan, flag, sumber, versi, dan kalimat bukan probabilitas', () => {
    const text = buildCopyText(DEMO_CHECKS['1.1.1.1'])
    expect(text).toContain('IP: 1.1.1.1')
    expect(text).toContain('Waktu: 03 Nov 2026 10:00:00 WIB, oleh tester')
    expect(text).toContain('Status penilaian: COMPLETE')
    expect(text).toContain('Skor gabungan: 77.0 (SANGAT_TINGGI)')
    expect(text).toContain('Cakupan: 2/2')
    expect(text).toContain('Flag: SUMBER_SIMULASI')
    expect(text).toContain('- AbuseIPDB: OK_SIGNAL, skor sumber 90')
    expect(text).toContain('scoring_version: v1-percobaan')
    expect(text).toContain('Skor = label indikasi untuk triase, bukan probabilitas.')
    expect(text).not.toContain('%')
  })

  it('hasil simulasi diberi tanda di baris pertama', () => {
    expect(buildCopyText(DEMO_CHECKS['1.1.1.1']).split('\n')[0]).toBe('*** SIMULASI · bukan data nyata ***')
    expect(buildCopyText(LEGACY_CHECK)).not.toContain('SIMULASI')
  })

  it('null menjadi N/A dan galat sumber membawa reason', () => {
    const text = buildCopyText(DEMO_CHECKS['8.8.8.8'])
    expect(text).toContain('Skor gabungan: N/A')
    expect(text).not.toContain('Skor gabungan: 0')
    expect(text).toContain('- VirusTotal: ERROR (TIMEOUT)')
  })
})

describe('pivotLinks', () => {
  it('dibuat hanya dari IPv4 yang valid', () => {
    expect(pivotLinks('118.25.6.39')).toEqual([
      { name: 'AbuseIPDB', href: 'https://www.abuseipdb.com/check/118.25.6.39' },
      { name: 'VirusTotal', href: 'https://www.virustotal.com/gui/ip-address/118.25.6.39' },
    ])
  })

  it.each([
    '', 'abc', '2001:db8::1', '1.2.3', '1.2.3.4.5', '256.1.1.1', '1.1.1.1/../x',
    'javascript:alert(1)', '1.1.1.1?x=1', '1.1.1.1 ', ' 1.1.1.1',
  ])('menolak %j', (value) => {
    expect(pivotLinks(value)).toEqual([])
  })
})
