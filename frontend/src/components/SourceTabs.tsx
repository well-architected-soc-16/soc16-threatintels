import type { ReactNode } from 'react'
import type { CheckOut, SourceResult } from '../api/types'
import {
  describeSource,
  describeVendorRatio,
  evidenceBool,
  evidenceNumber,
  flagText,
  formatCount,
  formatDuration,
  formatHttpStatus,
  formatNormalizedScore,
  cacheLabel,
  sourceName,
  sourceTimeLabel,
  vendorRatio,
  whitelistText,
  SIMULATION_FLAG,
} from '../lib/format'
import { CacheBadge, FlagChip } from './Badges'
import { FailureChip } from './Chip'
import { TimeText } from './TimeText'

// Semua nilai dari sumber (pihak ketiga) dirender sebagai teks React biasa; tidak ada HTML mentah (Aturan 7).

function Field({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-x-4 py-1.5 sm:grid-cols-[minmax(0,13rem)_1fr]">
      <dt className="text-padat text-redup">{label}</dt>
      <dd className="min-w-0 text-padat [overflow-wrap:anywhere]">{children}</dd>
    </div>
  )
}

const KEY = (name: string) => <code className="font-mono">{name}</code>

function StatusLine({ source }: { source: SourceResult }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      {source.status === 'ERROR' ? (
        <FailureChip>{source.status}</FailureChip>
      ) : (
        <code className="font-mono text-padat">{source.status}</code>
      )}
      <span className="text-padat text-redup">{describeSource(source)}</span>
      {source.reason && (
        <code className="font-mono text-kecil text-redup">{source.reason}</code>
      )}
    </div>
  )
}

// Jejak ambil data. Bidang yang tidak ada (check lama TASK-01) tampil "tidak tersedia", bukan dikosongkan.
function Meta({ source }: { source: SourceResult }) {
  return (
    <dl className="mt-3 border-t border-garis/35 pt-2">
      <Field label="Diambil">
        <TimeText iso={source.retrieved_at} />
      </Field>
      <Field label="Asal data">{cacheLabel(source) ?? 'tidak tersedia'}</Field>
      <Field label="Berlaku sampai">
        <TimeText iso={source.expires_at} />
      </Field>
      <Field label="HTTP status">{formatHttpStatus(source.http_status)}</Field>
      <Field label="Durasi">{formatDuration(source.duration_ms)}</Field>
    </dl>
  )
}

function SourceFlags({ source }: { source: SourceResult }) {
  const flags = source.flags.filter((flag) => flag !== SIMULATION_FLAG)
  if (flags.length === 0) return null
  return (
    <ul className="mt-2 flex flex-wrap gap-2">
      {flags.map((flag) => (
        <li key={flag} className="flex items-center gap-2 text-padat">
          <FlagChip flag={flag} />
          <span className="text-redup">{flagText(flag)}</span>
        </li>
      ))}
    </ul>
  )
}

// Label menurut source_time_type (Aturan tampilan 3): laporan terakhir / analisis terakhir; tanpa jenis = netral.
function SourceTimeField({ source }: { source: SourceResult }) {
  const typeLabel = sourceTimeLabel(source.source_time_type)
  const label =
    typeLabel === 'tidak tersedia'
      ? 'Waktu dari sumber'
      : typeLabel.charAt(0).toUpperCase() + typeLabel.slice(1)
  return (
    <Field label={label}>
      {source.source_time === null ? 'tidak tersedia' : <TimeText iso={source.source_time} />}
    </Field>
  )
}

function Missing({ name }: { name: string }) {
  return <p className="text-padat text-redup">Sumber {name} tidak ada pada pemeriksaan ini.</p>
}

export function SummaryTab({ check }: { check: CheckOut }) {
  return (
    <div className="space-y-4">
      {check.flags.includes('HASIL_BERBEDA') && (
        <div role="note" className="rounded-md border border-teks px-3 py-2 text-padat">
          <strong className="font-semibold">Hasil berbeda.</strong> {flagText('HASIL_BERBEDA')}.
        </div>
      )}
      {check.sources.length === 0 ? (
        <p className="text-padat text-redup">Tidak ada data sumber pada pemeriksaan ini.</p>
      ) : (
        <ul className="space-y-3">
          {check.sources.map((source) => (
            <li key={source.source} className="rounded-lg border border-garis/35 p-3">
              <h3 className="font-semibold">{sourceName(source.source)}</h3>
              <div className="mt-1">
                <StatusLine source={source} />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-padat">
                <span>
                  Skor sumber:{' '}
                  <span className="tabular-nums">
                    {formatNormalizedScore(source.normalized_score)}
                  </span>
                </span>
                <CacheBadge source={source} />
              </div>
              <SourceFlags source={source} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function AbuseTab({ source }: { source: SourceResult | undefined }) {
  if (!source) return <Missing name="AbuseIPDB" />
  const ev = source.evidence_summary
  const score = evidenceNumber(ev, 'abuseConfidenceScore')
  const reports = evidenceNumber(ev, 'totalReports')
  const users = evidenceNumber(ev, 'numDistinctUsers')
  const whitelisted = evidenceBool(ev, 'isWhitelisted')
  const hasEvidence = [score, reports, users, whitelisted].some((value) => value !== null)

  return (
    <div>
      <StatusLine source={source} />
      <SourceFlags source={source} />
      {hasEvidence ? (
        <dl className="mt-3">
          <Field label={KEY('abuseConfidenceScore')}>
            <span className="tabular-nums">{formatCount(score)}</span>
          </Field>
          <Field label={KEY('totalReports')}>
            <span className="tabular-nums">{formatCount(reports)}</span>
          </Field>
          <Field label={KEY('numDistinctUsers')}>
            <span className="tabular-nums">{formatCount(users)}</span>
          </Field>
          {/* Dari source_time (WIB, dari backend), bukan evidence.lastReportedAt yang UTC mentah. */}
          <SourceTimeField source={source} />
          <Field label={KEY('isWhitelisted')}>{whitelistText(whitelisted)}</Field>
        </dl>
      ) : (
        <p className="mt-3 text-padat text-redup">Tidak ada bukti dari sumber ini.</p>
      )}
      <Meta source={source} />
    </div>
  )
}

const VT_KEYS = ['malicious', 'suspicious', 'harmless', 'undetected', 'timeout'] as const

export function VirusTotalTab({ source }: { source: SourceResult | undefined }) {
  if (!source) return <Missing name="VirusTotal" />
  const ev = source.evidence_summary
  const counts = VT_KEYS.map((key) => [key, evidenceNumber(ev, key)] as const)
  const hasEvidence = counts.some(([, value]) => value !== null)

  return (
    <div>
      <StatusLine source={source} />
      <SourceFlags source={source} />
      {hasEvidence ? (
        <dl className="mt-3">
          {counts.map(([key, value]) => (
            <Field key={key} label={KEY(key)}>
              <span className="tabular-nums">{formatCount(value)}</span>
            </Field>
          ))}
          <Field label="Vendor menandai">{describeVendorRatio(vendorRatio(ev))}</Field>
          {/* Mock tidak punya last_analysis_date; null tampil "tidak tersedia". */}
          <SourceTimeField source={source} />
        </dl>
      ) : (
        <p className="mt-3 text-padat text-redup">Tidak ada bukti dari sumber ini.</p>
      )}
      <p className="mt-2 text-kecil text-redup">
        Rasio vendor bukan peluang IP jahat; ini hitungan mesin vendor yang menandai.
      </p>
      <Meta source={source} />
    </div>
  )
}

export function RawJsonTab({ check }: { check: CheckOut }) {
  return (
    <pre
      tabIndex={0}
      aria-label="Data pemeriksaan apa adanya (JSON)"
      className="max-h-[32rem] overflow-auto rounded-md border border-garis/35 bg-tanah p-3 font-mono text-padat"
    >
      {JSON.stringify(check, null, 2)}
    </pre>
  )
}
