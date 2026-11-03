import type { Indication, SourceResult } from '../api/types'
import { cacheLabel, indicationView } from '../lib/format'
import { Chip } from './Chip'
import { CHIP_TONE } from './tone'

// Label indikasi = teks + warna, dari field `indication` backend (tidak dihitung ulang).
export function LabelChip({ indication }: { indication: Indication | null }) {
  const view = indicationView(indication)
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-padat font-medium [overflow-wrap:anywhere] ${CHIP_TONE[view.tone]}`}
    >
      {view.code}
    </span>
  )
}

// Warna khusus non-verdict (ungu) + bingkai tebal bergaris diagonal + teks (Aturan tampilan 4).
export function SimulationTag() {
  return (
    <span className="simulasi-frame inline-block align-middle">
      <span className="block rounded-sm bg-simulasi-bg px-2 py-0.5 text-kecil font-medium text-simulasi">
        SIMULASI · bukan data nyata
      </span>
    </span>
  )
}

export function FlagChip({ flag }: { flag: string }) {
  return <Chip mono>{flag}</Chip>
}

// Hanya bila sumber punya retrieved_at; check lama TASK-01 tidak diberi label palsu "Ambil baru".
export function CacheBadge({
  source,
}: {
  source: Pick<SourceResult, 'retrieved_at' | 'from_cache'>
}) {
  const label = cacheLabel(source)
  return label === null ? null : <Chip>{label}</Chip>
}
