import type { CheckOut, SourceResult } from '../api/types'

// FIXTURE SINTETIS untuk uji tampilan. Bentuknya mengikuti CheckOut backend, tetapi angka gabungan
// (risk_score, normalized_score) hanyalah contoh, BUKAN hasil perhitungan backend dan jangan dipakai sebagai
// acuan skor. Yang diuji dari fixture ini adalah invarian tampilan, bukan rumus.

const NOW = '2026-11-03T10:00:00+07:00'
const LATER = '2026-11-03T16:00:00+07:00'

export function makeSource(
  over: Partial<SourceResult> & Pick<SourceResult, 'source' | 'status'>,
): SourceResult {
  return {
    reason: null,
    normalized_score: null,
    evidence_summary: {},
    source_time: null,
    source_time_type: null,
    retrieved_at: NOW,
    expires_at: LATER,
    from_cache: false,
    http_status: 200,
    duration_ms: 120,
    flags: ['SUMBER_SIMULASI'],
    retry_after_seconds: null,
    ...over,
  }
}

export function makeCheck(over: Partial<CheckOut> & Pick<CheckOut, 'ip'>): CheckOut {
  return {
    id: 1,
    assessment_status: 'COMPLETE',
    risk_score: null,
    scoring_version: 'v1-percobaan',
    coverage: '2/2',
    flags: ['SUMBER_SIMULASI'],
    sources: [],
    checked_by: 'tester',
    checked_at: NOW,
    indication: null,
    ...over,
  }
}

const abuse = (
  score: number,
  over: Partial<SourceResult> = {},
  whitelisted = false,
): SourceResult =>
  makeSource({
    source: 'abuseipdb',
    status: score > 0 ? 'OK_SIGNAL' : 'OK_NO_SIGNAL',
    normalized_score: score,
    source_time_type: 'last_report',
    evidence_summary: {
      abuseConfidenceScore: score,
      totalReports: score > 0 ? 120 : 0,
      numDistinctUsers: score > 0 ? 40 : 0,
      lastReportedAt: null,
      isWhitelisted: whitelisted,
      simulasi: true,
    },
    ...over,
  })

const vt = (
  stats: Record<string, number>,
  over: Partial<SourceResult> = {},
): SourceResult => {
  const flagged = (stats.malicious ?? 0) + (stats.suspicious ?? 0)
  return makeSource({
    source: 'virustotal',
    status: flagged > 0 ? 'OK_SIGNAL' : 'OK_NO_SIGNAL',
    normalized_score: flagged > 0 ? 40 : 0,
    source_time_type: 'last_analysis',
    evidence_summary: { ...stats, simulasi: true },
    ...over,
  })
}

const failed = (
  source: string,
  reason: SourceResult['reason'],
  over: Partial<SourceResult> = {},
): SourceResult =>
  makeSource({
    source,
    status: 'ERROR',
    reason,
    http_status: null,
    evidence_summary: { simulasi: true },
    ...over,
  })

const demo = (
  id: number,
  ip: string,
  over: Partial<CheckOut>,
  sources: SourceResult[],
): CheckOut => makeCheck({ id, ip, sources, ...over })

const CLEAN_VT = { malicious: 0, suspicious: 0, harmless: 60, undetected: 30, timeout: 0 }

export const DEMO_CHECKS: Record<string, CheckOut> = {
  '1.1.1.1': demo(
    1,
    '1.1.1.1',
    { risk_score: 77, indication: 'SANGAT_TINGGI' },
    [abuse(90), vt({ malicious: 10, suspicious: 0, harmless: 50, undetected: 30, timeout: 0 })],
  ),
  '1.0.0.1': demo(
    2,
    '1.0.0.1',
    {
      risk_score: 49.1,
      indication: 'PERLU_PEMERIKSAAN',
      flags: ['HASIL_BERBEDA', 'SUMBER_SIMULASI'],
    },
    [abuse(90), vt(CLEAN_VT)],
  ),
  '8.8.8.8': demo(
    3,
    '8.8.8.8',
    { assessment_status: 'DATA_TERBATAS', coverage: '1/2' },
    [abuse(90), failed('virustotal', 'TIMEOUT')],
  ),
  '8.8.4.4': demo(
    4,
    '8.8.4.4',
    { assessment_status: 'TIDAK_TERSEDIA', coverage: '0/2' },
    [
      failed('abuseipdb', 'TIMEOUT'),
      makeSource({
        source: 'virustotal',
        status: 'NO_RECORD',
        evidence_summary: { simulasi: true },
      }),
    ],
  ),
  '9.9.9.9': demo(
    5,
    '9.9.9.9',
    {
      risk_score: 77,
      indication: 'SANGAT_TINGGI',
      flags: ['WHITELISTED', 'SUMBER_SIMULASI'],
    },
    [
      abuse(90, {}, true),
      vt({ malicious: 10, suspicious: 0, harmless: 50, undetected: 30, timeout: 0 }),
    ],
  ),
  '149.112.112.112': demo(
    6,
    '149.112.112.112',
    {
      risk_score: 0,
      indication: 'RENDAH',
      flags: ['NO_VENDOR_OPINION', 'SUMBER_SIMULASI'],
    },
    [
      abuse(0),
      vt(
        { malicious: 0, suspicious: 0, harmless: 0, undetected: 90, timeout: 0 },
        { flags: ['NO_VENDOR_OPINION', 'SUMBER_SIMULASI'] },
      ),
    ],
  ),
  '208.67.222.222': demo(
    7,
    '208.67.222.222',
    { assessment_status: 'DATA_TERBATAS', coverage: '1/2' },
    [
      abuse(0),
      vt(
        { malicious: 0, suspicious: 0, harmless: 0, undetected: 0, timeout: 90 },
        { status: 'INSUFFICIENT_DATA', normalized_score: null },
      ),
    ],
  ),
}

// Check lama dari TASK-01: sumber hanya punya source/status/reason; sisanya bawaan skema backend
// (retrieved_at null, from_cache false, evidence kosong, tanpa flag).
export const LEGACY_CHECK: CheckOut = makeCheck({
  id: 99,
  ip: '203.0.113.9',
  assessment_status: 'TIDAK_TERSEDIA',
  coverage: '0/2',
  scoring_version: 'v0',
  flags: [],
  sources: [
    makeSource({
      source: 'abuseipdb',
      status: 'SKIPPED',
      reason: 'ADAPTER_NOT_IMPLEMENTED',
      retrieved_at: null,
      expires_at: null,
      http_status: null,
      duration_ms: null,
      flags: [],
    }),
    makeSource({
      source: 'virustotal',
      status: 'SKIPPED',
      reason: 'ADAPTER_NOT_IMPLEMENTED',
      retrieved_at: null,
      expires_at: null,
      http_status: null,
      duration_ms: null,
      flags: [],
    }),
  ],
})
