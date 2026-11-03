import type { CheckOut } from '../api/types'
import {
  assessmentText,
  contributes,
  formatScore,
  indicationView,
  isSimulated,
  sourceName,
} from '../lib/format'
import { LabelChip, SimulationTag } from './Badges'
import { TimeText } from './TimeText'
import { STRIP_TONE } from './tone'

// Pengukur cakupan: satu sel bernama per sumber. Terisi bila menjawab; putus-putus + kode bila tidak.
function CoverageMeter({ check }: { check: CheckOut }) {
  if (check.sources.length === 0) {
    return <p className="mt-2 text-padat text-redup">Tidak ada data sumber.</p>
  }
  return (
    <ul className="mt-2 flex flex-wrap gap-2" aria-label="Sumber yang menjawab">
      {check.sources.map((source) =>
        contributes(source.status) ? (
          <li
            key={source.source}
            className="rounded-md bg-teks px-3 py-1.5 text-padat text-tanah"
          >
            <span className="font-medium">{sourceName(source.source)}</span> menjawab
          </li>
        ) : (
          <li
            key={source.source}
            className="rounded-md border border-dashed border-garis px-3 py-1.5 text-padat text-redup"
          >
            <span className="font-medium">{sourceName(source.source)}</span> tidak menjawab{' '}
            <code className="font-mono text-kecil">
              {source.status}
              {source.reason ? ` · ${source.reason}` : ''}
            </code>
          </li>
        ),
      )}
    </ul>
  )
}

// Satu-satunya tempat "berani": blok skor solid berwarna verdict, label, dan cakupan (Keputusan 13e).
export function SummaryStrip({ check }: { check: CheckOut }) {
  const view = indicationView(check.indication)
  const simulated = isSimulated(check)
  const noScore = check.risk_score === null

  const body = (
    <div className="rounded-lg bg-panel p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h2 className="font-mono text-judul font-semibold">{check.ip}</h2>
        <code className="font-mono text-padat text-redup">{check.assessment_status}</code>
        {simulated && <SimulationTag />}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-4">
        <div
          className={`min-w-32 rounded-lg px-5 py-3 text-center text-skor font-bold tabular-nums ${STRIP_TONE[view.tone]}`}
        >
          <span className="sr-only">Skor gabungan: </span>
          {formatScore(check.risk_score)}
        </div>

        <div className="min-w-0 flex-1 basis-60">
          <p className="flex flex-wrap items-center gap-2">
            <LabelChip indication={check.indication} />
            {!noScore && <span className="text-isi">{view.text}</span>}
          </p>
          {noScore && (
            <p className="mt-1 text-padat text-redup">
              Skor gabungan tidak dihitung: {assessmentText(check.assessment_status)}.
            </p>
          )}
          <p className="mt-2 text-padat">
            Cakupan <span className="font-semibold tabular-nums">{check.coverage}</span>
          </p>
          <CoverageMeter check={check} />
        </div>
      </div>

      <p className="mt-3 tabular-nums text-padat text-redup">
        Diperiksa <TimeText iso={check.checked_at} /> oleh {check.checked_by}
      </p>
    </div>
  )

  return (
    <section aria-label="Ringkasan pemeriksaan">
      {simulated ? (
        <div className="simulasi-frame">{body}</div>
      ) : (
        <div className="rounded-lg border border-garis/35">{body}</div>
      )}
    </section>
  )
}
