import { useState } from 'react'
import type { CheckOut } from '../api/types'
import { formatScore, formatTime, isSimulated } from '../lib/format'
import { filterHistory, hasMore } from '../lib/history'
import type { WorkbenchState } from '../workbench/store'
import { LabelChip, SimulationTag } from './Badges'
import { Button } from './Button'
import { IconX } from './Icon'

interface HistoryRailProps {
  state: Pick<
    WorkbenchState,
    'history' | 'total' | 'historyStatus' | 'historyError' | 'loadingMore' | 'selected'
  >
  onSelect: (id: number) => void
  onLoadMore: () => void
  onRetry: () => void
}

function HistoryRow({
  check,
  active,
  onSelect,
}: {
  check: CheckOut
  active: boolean
  onSelect: (id: number) => void
}) {
  return (
    <li>
      <button
        type="button"
        aria-current={active ? 'true' : undefined}
        onClick={() => onSelect(check.id)}
        className={`w-full rounded-md border px-3 py-2 text-left transition-colors duration-150 ${
          active ? 'border-aksen bg-tanah' : 'border-transparent hover:bg-tanah'
        }`}
      >
        <span className="flex items-baseline justify-between gap-2">
          <span className="font-mono text-padat">{check.ip}</span>
          <span className="tabular-nums text-padat text-redup">
            {formatScore(check.risk_score)}
          </span>
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-1.5">
          <LabelChip indication={check.indication} />
        </span>
        <span className="mt-1 block tabular-nums text-kecil text-redup">
          {formatTime(check.checked_at)}
        </span>
        {isSimulated(check) && (
          <span className="mt-1 block">
            <SimulationTag />
          </span>
        )}
      </button>
    </li>
  )
}

export function HistoryRail({ state, onSelect, onLoadMore, onRetry }: HistoryRailProps) {
  const [query, setQuery] = useState('')
  const { history, total, historyStatus, historyError, loadingMore, selected } = state
  const visible = filterHistory(history, query)

  return (
    <>
      <h2 className="text-sub font-semibold">Riwayat</h2>

      {historyStatus === 'loading' && history.length === 0 && (
        <p role="status" className="mt-2 text-padat text-redup">
          Memuat riwayat…
        </p>
      )}

      {historyError !== null && (
        <div
          role="alert"
          className="mt-2 flex items-start gap-1.5 rounded-md border border-gagal px-2 py-1 text-padat text-gagal"
        >
          <IconX className="mt-0.5 size-3.5 shrink-0" />
          <span className="min-w-0 flex-1">{historyError}</span>
        </div>
      )}
      {historyStatus === 'error' && (
        <Button variant="secondary" onClick={onRetry} className="mt-2 w-full">
          Coba lagi
        </Button>
      )}

      {historyStatus === 'ready' && history.length === 0 && (
        <p className="mt-2 text-padat text-redup">Belum ada pemeriksaan.</p>
      )}

      {history.length > 0 && (
        <>
          <div className="mt-3">
            <label htmlFor="history-filter" className="mb-1 block text-padat text-redup">
              Saring IP
            </label>
            <input
              id="history-filter"
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-describedby="history-filter-note"
              className="w-full rounded-md border border-garis bg-tanah px-3 py-1.5 font-mono text-padat text-teks"
            />
            <p id="history-filter-note" className="mt-1 text-kecil text-redup">
              Menyaring yang sudah dimuat, bukan seluruh riwayat.
            </p>
          </div>

          {visible.length === 0 ? (
            <p className="mt-3 text-padat text-redup">
              Tidak ada IP yang cocok di antara yang sudah dimuat.
            </p>
          ) : (
            <ul className="mt-3 space-y-1">
              {visible.map((check) => (
                <HistoryRow
                  key={check.id}
                  check={check}
                  active={selected?.id === check.id}
                  onSelect={onSelect}
                />
              ))}
            </ul>
          )}

          <p className="mt-3 tabular-nums text-kecil text-redup">
            {history.length}
            {total !== null ? ` dari ${total}` : ''} dimuat
          </p>
          {hasMore(history.length, total) && (
            <Button
              variant="secondary"
              onClick={onLoadMore}
              disabled={loadingMore}
              className="mt-2 w-full"
            >
              {loadingMore ? 'Memuat…' : 'Muat lagi'}
            </Button>
          )}
        </>
      )}
    </>
  )
}
