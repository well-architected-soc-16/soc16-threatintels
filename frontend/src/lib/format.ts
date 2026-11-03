import type {
  AssessmentStatus,
  CheckOut,
  Flag,
  Indication,
  SourceReason,
  SourceResult,
  SourceStatus,
  SourceTimeType,
} from '../api/types'

// Semua teks tampilan diturunkan dari data backend di sini, sebagai fungsi murni yang diuji. Nilai dari backend
// bertipe `str` untuk reason/flag/status, jadi pencarian kamus memakai Object.hasOwn (kunci seperti
// "constructor" tidak boleh menarik properti prototipe) dan selalu punya cadangan berupa kode aslinya.

function lookup<T>(map: Record<string, T>, key: string): T | undefined {
  return Object.hasOwn(map, key) ? map[key] : undefined
}

// ---------- Skor ----------

// Skor gabungan: null bukan 0 (Aturan tampilan 1). Tanpa tanda persen (Aturan tampilan 2).
export function formatScore(score: number | null | undefined): string {
  if (typeof score !== 'number' || !Number.isFinite(score)) return 'N/A'
  return score.toFixed(1)
}

// Skor ternormalisasi per sumber: null menjadi "—".
export function formatNormalizedScore(score: number | null | undefined): string {
  if (typeof score !== 'number' || !Number.isFinite(score)) return '—'
  return String(score)
}

// ---------- Label indikasi ----------

export type Tone = 'rendah' | 'perlu' | 'tinggi' | 'sangat' | 'na'

export interface IndicationView {
  tone: Tone
  // Kode asli dari backend (atau "N/A").
  code: string
  // Penjelasan sesuai tabel label di Aturan tampilan.
  text: string
}

const INDICATIONS: Record<Indication, { tone: Tone; text: string }> = {
  RENDAH: { tone: 'rendah', text: 'Indikasi rendah · tetap baca bukti' },
  PERLU_PEMERIKSAAN: { tone: 'perlu', text: 'Perlu pemeriksaan' },
  TINGGI: { tone: 'tinggi', text: 'Indikasi tinggi · dahulukan pemeriksaan' },
  SANGAT_TINGGI: {
    tone: 'sangat',
    text: 'Indikasi sangat tinggi · periksa segera, tanpa auto-block',
  },
}

// Label HANYA dari field `indication` backend, tidak pernah dihitung ulang dari skor (Keputusan 7).
export function indicationView(
  indication: Indication | null | undefined,
): IndicationView {
  if (indication === null || indication === undefined) {
    return { tone: 'na', code: 'N/A', text: 'N/A' }
  }
  const known = lookup(INDICATIONS, indication)
  if (known) return { tone: known.tone, code: indication, text: known.text }
  return { tone: 'na', code: String(indication), text: String(indication) }
}

const ASSESSMENT_TEXT: Record<AssessmentStatus, string> = {
  COMPLETE: 'kedua sumber menjawab',
  DATA_TERBATAS: 'hanya satu sumber yang menjawab',
  TIDAK_TERSEDIA: 'tidak ada sumber yang menjawab',
}

export function assessmentText(status: string): string {
  return lookup(ASSESSMENT_TEXT, status) ?? 'status penilaian tidak dikenal'
}

// ---------- Sumber ----------

const SOURCE_NAMES: Record<string, string> = {
  abuseipdb: 'AbuseIPDB',
  virustotal: 'VirusTotal',
}

export function sourceName(source: string): string {
  return lookup(SOURCE_NAMES, source) ?? source
}

const STATUS_TEXT: Record<SourceStatus, string> = {
  OK_SIGNAL: 'ada sinyal buruk',
  OK_NO_SIGNAL: 'tidak ada sinyal buruk pada data ini (bukan jaminan aman)',
  NO_RECORD: 'sumber tidak punya catatan untuk IP ini',
  INSUFFICIENT_DATA: 'data sumber tidak cukup untuk dinilai',
  ERROR: 'sumber gagal',
  SKIPPED: 'dilewati',
}

const REASON_TEXT: Record<SourceReason, string> = {
  AUTH: 'autentikasi ke sumber ditolak (periksa API key)',
  RATE_LIMIT: 'kuota atau batas laju sumber tercapai',
  TIMEOUT: 'sumber tidak menjawab tepat waktu',
  UPSTREAM: 'layanan sumber bermasalah',
  INVALID_RESPONSE: 'respons sumber tidak dapat dibaca',
  INTERNAL_ERROR: 'galat internal di sisi tool ini',
  ADAPTER_NOT_IMPLEMENTED: 'adapter sumber belum diimplementasikan',
  QUOTA_INTERNAL: 'kuota internal tool ini habis',
}

export function reasonText(reason: string | null | undefined): string {
  if (reason === null || reason === undefined || reason === '') {
    return 'alasan tidak dicatat'
  }
  return lookup(REASON_TEXT, reason) ?? 'alasan tidak dikenal'
}

// "coba lagi ±N detik" hanya untuk angka positif yang masuk akal.
export function retryText(seconds: number | null | undefined): string | null {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds <= 0) {
    return null
  }
  return `coba lagi ±${Math.ceil(seconds)} detik`
}

// Penjelasan status sumber; kode aslinya ditampilkan terpisah (monospace) oleh pemanggil.
export function describeSource(
  source: Pick<SourceResult, 'status' | 'reason' | 'retry_after_seconds'>,
): string {
  const base = lookup(STATUS_TEXT, source.status)
  if (base === undefined) return 'status sumber tidak dikenal'
  if (source.status === 'ERROR' || source.status === 'SKIPPED') {
    const parts = [`${base}: ${reasonText(source.reason)}`]
    if (source.reason === 'RATE_LIMIT') {
      const retry = retryText(source.retry_after_seconds)
      if (retry) parts.push(retry)
    }
    return parts.join('; ')
  }
  return base
}

// Hanya OK_SIGNAL dan OK_NO_SIGNAL yang menambah cakupan (CLAUDE.md).
export function contributes(status: string): boolean {
  return status === 'OK_SIGNAL' || status === 'OK_NO_SIGNAL'
}

export function silentSources(
  check: Pick<CheckOut, 'sources'>,
): SourceResult[] {
  return check.sources.filter((source) => !contributes(source.status))
}

export function findSource(
  check: Pick<CheckOut, 'sources'>,
  name: string,
): SourceResult | undefined {
  return check.sources.find((source) => source.source === name)
}

// Badge cache hanya bila sumber punya retrieved_at. Check lama TASK-01 tidak punya field itu dan datang
// dengan from_cache=false bawaan; tanpa penjagaan ini semuanya akan salah berlabel "Ambil baru".
export function cacheLabel(
  source: Pick<SourceResult, 'retrieved_at' | 'from_cache'>,
): 'Cache' | 'Ambil baru' | null {
  if (source.retrieved_at === null || source.retrieved_at === undefined) {
    return null
  }
  return source.from_cache ? 'Cache' : 'Ambil baru'
}

const TIME_TYPE_TEXT: Record<SourceTimeType, string> = {
  last_report: 'laporan terakhir',
  last_analysis: 'analisis terakhir',
}

export function sourceTimeLabel(type: string | null | undefined): string {
  if (type === null || type === undefined) return 'tidak tersedia'
  return lookup(TIME_TYPE_TEXT, type) ?? 'tidak tersedia'
}

// ---------- Flag ----------

export const SIMULATION_FLAG = 'SUMBER_SIMULASI'

const FLAG_TEXT: Record<Flag, string> = {
  HASIL_BERBEDA: 'kedua sumber tidak sepakat (selisih ≥ 50), baca bukti keduanya',
  NO_VENDOR_OPINION: 'vendor VirusTotal tidak memberi opini',
  WHITELISTED:
    'AbuseIPDB menandai whitelist; skor tidak dipotong, butuh review analis',
  SUMBER_SIMULASI: 'hasil simulasi, bukan data nyata',
}

export function flagText(flag: string): string {
  return lookup(FLAG_TEXT, flag) ?? 'flag tidak dikenal'
}

// Hasil simulasi terbaca dari flag tingkat-check (ada di urutan flag backend) maupun flag sumber.
export function isSimulated(
  check: Pick<CheckOut, 'flags' | 'sources'>,
): boolean {
  return (
    check.flags.includes(SIMULATION_FLAG) ||
    check.sources.some((source) => source.flags.includes(SIMULATION_FLAG))
  )
}

// ---------- Waktu ----------

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
const WIB_TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?\+07:00$/

// "02 Nov 2026 14:03:07 WIB" HANYA bila string berakhiran +07:00. String lain (mis. +00:00 milik
// evidence_summary.lastReportedAt) tampil mentah dan tidak pernah diberi label WIB. Tanpa new Date():
// tidak ada konversi zona (Keputusan 20).
export function formatTime(iso: string | null | undefined): string {
  if (typeof iso !== 'string') return 'tidak tersedia'
  const match = WIB_TIME.exec(iso)
  if (!match) return iso
  const [, year, month, day, hour, minute, second] = match
  const monthIndex = Number(month)
  if (
    monthIndex < 1 ||
    monthIndex > 12 ||
    Number(day) < 1 ||
    Number(day) > 31 ||
    Number(hour) > 23 ||
    Number(minute) > 59 ||
    Number(second) > 59
  ) {
    return iso
  }
  return `${day} ${MONTHS[monthIndex - 1]} ${year} ${hour}:${minute}:${second} WIB`
}

// ---------- Bukti (evidence_summary, data pihak ketiga: dibaca defensif) ----------

export function evidenceNumber(
  evidence: Record<string, unknown> | null | undefined,
  key: string,
): number | null {
  if (!evidence || !Object.hasOwn(evidence, key)) return null
  const value = evidence[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function evidenceBool(
  evidence: Record<string, unknown> | null | undefined,
  key: string,
): boolean | null {
  if (!evidence || !Object.hasOwn(evidence, key)) return null
  const value = evidence[key]
  return typeof value === 'boolean' ? value : null
}

export function formatCount(value: number | null): string {
  return value === null ? '—' : String(value)
}

export function formatDuration(ms: number | null | undefined): string {
  return typeof ms === 'number' && Number.isFinite(ms) ? `${ms} ms` : '—'
}

export function formatHttpStatus(status: number | null | undefined): string {
  return typeof status === 'number' && Number.isFinite(status) ? String(status) : '—'
}

export function whitelistText(value: boolean | null): string {
  if (value === null) return 'tidak diketahui'
  return value ? 'ya' : 'tidak'
}

const VENDOR_KEYS = ['malicious', 'suspicious', 'harmless', 'undetected'] as const

export interface VendorRatio {
  flagged: number
  total: number
  // Kategori yang tidak ada di respons sumber.
  missing: string[]
}

// Rasio vendor VirusTotal dihitung dari key yang ADA saja; bukan probabilitas.
export function vendorRatio(
  evidence: Record<string, unknown> | null | undefined,
): VendorRatio | null {
  const values = VENDOR_KEYS.map((key) => [key, evidenceNumber(evidence, key)] as const)
  const present = values.filter(([, value]) => value !== null)
  if (present.length === 0) return null
  const sum = (keys: readonly string[]) =>
    present
      .filter(([key]) => keys.includes(key))
      .reduce((total, [, value]) => total + (value ?? 0), 0)
  return {
    flagged: sum(['malicious', 'suspicious']),
    total: sum(VENDOR_KEYS),
    missing: values.filter(([, value]) => value === null).map(([key]) => key),
  }
}

export function describeVendorRatio(ratio: VendorRatio | null): string {
  if (ratio === null) return '—'
  // Penyebut 0 (mis. semua vendor timeout) tidak pernah ditampilkan sebagai 0/0.
  if (ratio.total === 0) return 'tidak ada vendor yang menilai'
  const base = `${ratio.flagged} / ${ratio.total} vendor`
  return ratio.missing.length > 0
    ? `${base} (sebagian kategori tidak ada di respons sumber)`
    : base
}

// ---------- Salin hasil dan pivot ----------

export function buildCopyText(check: CheckOut): string {
  const view = indicationView(check.indication)
  const score =
    check.risk_score === null
      ? 'N/A'
      : `${formatScore(check.risk_score)} (${view.code})`
  const lines = [
    ...(isSimulated(check) ? ['*** SIMULASI · bukan data nyata ***'] : []),
    `IP: ${check.ip}`,
    `Waktu: ${formatTime(check.checked_at)}, oleh ${check.checked_by}`,
    `Status penilaian: ${check.assessment_status}`,
    `Skor gabungan: ${score}`,
    `Cakupan: ${check.coverage}`,
    `Flag: ${check.flags.length > 0 ? check.flags.join(', ') : 'tidak ada'}`,
    'Sumber:',
    ...check.sources.map((source) => {
      const detail =
        source.status === 'ERROR' || source.status === 'SKIPPED'
          ? ` (${source.reason ?? 'alasan tidak dicatat'})`
          : source.normalized_score === null
            ? ''
            : `, skor sumber ${source.normalized_score}`
      return `- ${sourceName(source.source)}: ${source.status}${detail}`
    }),
    `scoring_version: ${check.scoring_version}`,
    'Skor = label indikasi untuk triase, bukan probabilitas.',
  ]
  return lines.join('\n')
}

const IPV4 = /^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$/

export interface PivotLink {
  name: string
  href: string
}

// Tautan pivot hanya dibuat dari check.ip yang berbentuk IPv4 (pertahanan berlapis terhadap data aneh).
// Format URL belum diverifikasi dari dokumentasi resmi masing-masing situs (lihat TASK-03-progress.md).
export function pivotLinks(ip: string): PivotLink[] {
  if (!IPV4.test(ip)) return []
  const encoded = encodeURIComponent(ip)
  return [
    { name: 'AbuseIPDB', href: `https://www.abuseipdb.com/check/${encoded}` },
    { name: 'VirusTotal', href: `https://www.virustotal.com/gui/ip-address/${encoded}` },
  ]
}
