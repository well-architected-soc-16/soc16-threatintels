import type { MispState } from '../workbench/mispStore'
import { hasMore } from '../lib/history'
import { PENDING_HINT } from '../lib/misp'
import { IocStatusChip } from './Badges'
import { Button } from './Button'
import { Chip } from './Chip'
import { ExpandableText } from './ExpandableText'
import { IconX } from './Icon'
import { TimeText } from './TimeText'

interface MispViewProps {
  state: Pick<MispState, 'items' | 'total' | 'status' | 'error' | 'loadingMore'>
  onLoadMore: () => void
  onRefresh: () => void
  // Buka check terkait di Workbench.
  onOpenCheck: (checkId: number) => void
}

const TH = 'whitespace-nowrap px-3 py-2 text-left text-padat font-semibold'
const TD = 'px-3 py-2 align-top text-padat'

// Tabel polos GET /iocs: semua kiriman semua pengguna, terbaru di atas. Semua isi (alasan, tag, galat) adalah
// teks; tidak ada HTML dari data.
export function MispView({ state, onLoadMore, onRefresh, onOpenCheck }: MispViewProps) {
  const { items, total, status, error, loadingMore } = state

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-judul font-semibold">Kiriman MISP</h1>
        <Button variant="secondary" onClick={onRefresh} disabled={status === 'loading'}>
          {status === 'loading' ? 'Memuat…' : 'Segarkan'}
        </Button>
      </div>
      <p className="mt-1 text-padat text-redup">
        Semua kiriman dari seluruh pengguna, terbaru di atas. Mode mock menulis &quot;Terkirim (mock)&quot;, bukan
        terkirim ke MISP sungguhan.
      </p>

      {error !== null && (
        <p
          role="alert"
          className="mt-3 flex items-start gap-1.5 rounded-md border border-gagal px-2 py-1 text-padat text-gagal"
        >
          <IconX className="mt-0.5 size-3.5 shrink-0" />
          <span>{error}</span>
        </p>
      )}

      {(status === 'idle' || status === 'loading') && items.length === 0 && (
        <p role="status" className="mt-3 text-padat text-redup">
          Memuat daftar kiriman…
        </p>
      )}

      {status === 'ready' && items.length === 0 && (
        <p className="mt-3 text-isi text-redup">Belum ada kiriman ke MISP.</p>
      )}

      {items.length > 0 && (
        <>
          <div
            role="region"
            aria-label="Tabel kiriman MISP"
            tabIndex={0}
            className="mt-3 overflow-x-auto rounded-md border border-garis/35"
          >
            <table className="w-full min-w-[56rem] border-collapse">
              <thead className="border-b border-garis/35 bg-panel">
                <tr>
                  <th scope="col" className={TH}>Waktu</th>
                  <th scope="col" className={TH}>IP</th>
                  <th scope="col" className={TH}>Status</th>
                  <th scope="col" className={TH}>Event UUID</th>
                  <th scope="col" className={TH}>Pengirim</th>
                  <th scope="col" className={TH}>Alasan</th>
                  <th scope="col" className={TH}>Keterangan</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-garis/20 last:border-b-0">
                    <td className={`${TD} whitespace-nowrap tabular-nums`}>
                      <TimeText iso={item.submitted_at} />
                    </td>
                    <td className={TD}>
                      <span className="font-mono">{item.ip}</span>
                      <button
                        type="button"
                        onClick={() => onOpenCheck(item.check_id)}
                        className="mt-0.5 block text-kecil text-aksen underline underline-offset-2"
                      >
                        Buka check #{item.check_id}
                      </button>
                    </td>
                    <td className={TD}>
                      <IocStatusChip status={item.status} />
                    </td>
                    <td className={TD}>
                      {item.misp_event_uuid !== null ? (
                        <code className="font-mono text-kecil [overflow-wrap:anywhere]">
                          {item.misp_event_uuid}
                        </code>
                      ) : (
                        <span className="text-redup">—</span>
                      )}
                    </td>
                    <td className={TD}>{item.submitted_by}</td>
                    <td className={`${TD} max-w-80`}>
                      <ExpandableText text={item.reason} />
                      {item.tags.length > 0 && (
                        <span className="mt-1 flex flex-wrap gap-1">
                          {item.tags.map((tag, index) => (
                            <Chip key={`${index}-${tag}`} mono>
                              {tag}
                            </Chip>
                          ))}
                        </span>
                      )}
                    </td>
                    <td className={`${TD} max-w-64`}>
                      {item.status === 'failed' && item.error_message !== null && (
                        <span className="text-gagal [overflow-wrap:anywhere]">{item.error_message}</span>
                      )}
                      {item.status === 'pending' && <span className="text-redup">{PENDING_HINT}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 tabular-nums text-kecil text-redup">
            {items.length}
            {total !== null ? ` dari ${total}` : ''} dimuat
          </p>
          {hasMore(items.length, total) && (
            <Button variant="secondary" onClick={onLoadMore} disabled={loadingMore} className="mt-2">
              {loadingMore ? 'Memuat…' : 'Muat lagi'}
            </Button>
          )}
        </>
      )}
    </>
  )
}
