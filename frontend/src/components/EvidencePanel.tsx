import { useState } from 'react'
import type { CheckOut } from '../api/types'
import { findSource } from '../lib/format'
import { IconX } from './Icon'
import { AbuseTab, RawJsonTab, SummaryTab, VirusTotalTab } from './SourceTabs'
import { SummaryStrip } from './SummaryStrip'
import { panelId, tabId } from './tabIds'
import { Tabs, type TabDef } from './Tabs'

const TABS: readonly TabDef[] = [
  { id: 'ringkasan', label: 'Ringkasan' },
  { id: 'abuseipdb', label: 'AbuseIPDB' },
  { id: 'virustotal', label: 'VirusTotal' },
  { id: 'raw', label: 'Raw JSON' },
]

const PREFIX = 'bukti'

// `key` pada pemanggil mengatur ulang tab ke Ringkasan setiap berganti pemeriksaan.
function CheckView({ check }: { check: CheckOut }) {
  const [active, setActive] = useState('ringkasan')
  return (
    <div className="space-y-4">
      <SummaryStrip check={check} />
      <div>
        <Tabs tabs={TABS} active={active} onChange={setActive} prefix={PREFIX} label="Bukti per sumber" />
        <div
          role="tabpanel"
          id={panelId(PREFIX, active)}
          aria-labelledby={tabId(PREFIX, active)}
          tabIndex={0}
          className="pt-4"
        >
          {active === 'ringkasan' && <SummaryTab check={check} />}
          {active === 'abuseipdb' && <AbuseTab source={findSource(check, 'abuseipdb')} />}
          {active === 'virustotal' && <VirusTotalTab source={findSource(check, 'virustotal')} />}
          {active === 'raw' && <RawJsonTab check={check} />}
        </div>
      </div>
    </div>
  )
}

interface EvidencePanelProps {
  selected: CheckOut | null
  detailLoading: boolean
  detailError: string | null
  submitting: boolean
  canRun: boolean
}

export function EvidencePanel({
  selected,
  detailLoading,
  detailError,
  submitting,
  canRun,
}: EvidencePanelProps) {
  return (
    <>
      <h1 className="sr-only">Workbench investigasi IP</h1>

      {submitting && (
        <div role="status" className="mb-4">
          <p className="text-padat">Memeriksa… bisa sampai belasan detik.</p>
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-garis/35">
            <div className="bar-indeterminate h-full w-2/5 rounded-full bg-aksen" />
          </div>
        </div>
      )}

      {detailError !== null && (
        <p
          role="alert"
          className="mb-4 flex items-start gap-1.5 rounded-md border border-gagal px-2 py-1 text-padat text-gagal"
        >
          <IconX className="mt-0.5 size-3.5 shrink-0" />
          <span>{detailError}</span>
        </p>
      )}

      {selected === null ? (
        <p className="text-isi text-redup">
          {canRun
            ? 'Masukkan IPv4 publik di kolom pencarian, atau pilih pemeriksaan dari riwayat.'
            : 'Pilih pemeriksaan dari riwayat.'}
        </p>
      ) : (
        <>
          {detailLoading && (
            <p role="status" className="mb-2 text-kecil text-redup">
              Menyegarkan detail…
            </p>
          )}
          <CheckView key={selected.id} check={selected} />
        </>
      )}
    </>
  )
}
