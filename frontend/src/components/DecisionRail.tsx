import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { CheckOut } from '../api/types'
import {
  buildCopyText,
  cacheLabel,
  flagText,
  isSimulated,
  pivotLinks,
  silentSources,
  sourceName,
} from '../lib/format'
import { Button } from './Button'
import { FlagChip } from './Badges'
import { IconCheck, IconExternal } from './Icon'
import { TimeText } from './TimeText'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-garis/35 pt-3 first:border-t-0 first:pt-0">
      <h3 className="text-isi font-semibold">{title}</h3>
      <div className="mt-1.5 space-y-1.5 text-padat">{children}</div>
    </section>
  )
}

// Clipboard API hanya ada di konteks aman (HTTPS atau localhost). Lewat http://<IP-laptop>:5173 (sesi dev:lan)
// ia tidak ada, jadi cadangan berupa teks yang sudah terpilih di <textarea> adalah jalur normal, bukan galat.
function CopyResult({ text }: { text: string }) {
  const [mode, setMode] = useState<'idle' | 'copied' | 'manual'>('idle')
  const areaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (mode === 'manual') {
      areaRef.current?.focus()
      areaRef.current?.select()
    }
  }, [mode])

  async function copy() {
    if (window.isSecureContext && navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(text)
        setMode('copied')
        return
      } catch {
        // Ditolak izin atau gagal: lanjut ke cadangan manual.
      }
    }
    setMode('manual')
  }

  return (
    <div>
      <Button variant="secondary" onClick={() => void copy()} className="w-full">
        Salin hasil
      </Button>
      {mode === 'copied' && (
        <p role="status" className="mt-1.5 flex items-center gap-1.5 text-padat">
          <IconCheck className="size-3.5" />
          Tersalin
        </p>
      )}
      {mode === 'manual' && (
        <div className="mt-2">
          <label htmlFor="copy-manual" className="mb-1 block text-kecil text-redup">
            Penyalinan otomatis tidak tersedia di koneksi ini. Teks sudah terpilih; tekan Ctrl+C.
          </label>
          <textarea
            id="copy-manual"
            ref={areaRef}
            readOnly
            rows={9}
            value={text}
            className="w-full rounded-md border border-garis bg-tanah p-2 font-mono text-kecil text-teks"
          />
        </div>
      )}
    </div>
  )
}

interface DecisionRailProps {
  check: CheckOut | null
  canRun: boolean
  submitting: boolean
  onRerun: (ip: string) => void
}

export function DecisionRail({ check, canRun, submitting, onRerun }: DecisionRailProps) {
  if (check === null) {
    return (
      <>
        <h2 className="text-sub font-semibold">Keputusan</h2>
        <p className="mt-2 text-padat text-redup">Aksi muncul setelah ada hasil pengecekan.</p>
      </>
    )
  }

  const silent = silentSources(check)
  const simulated = isSimulated(check)
  const links = pivotLinks(check.ip)

  return (
    <div className="space-y-3">
      <h2 className="text-sub font-semibold">Keputusan</h2>

      <Section title="Cakupan">
        <p>
          <span className="font-semibold tabular-nums">{check.coverage}</span> sumber menjawab
        </p>
        {silent.length > 0 && (
          <ul className="space-y-1">
            {silent.map((source) => (
              <li key={source.source} className="text-redup">
                <span className="text-teks">{sourceName(source.source)}</span> tidak menjawab:{' '}
                <code className="font-mono text-kecil">
                  {source.status}
                  {source.reason ? ` · ${source.reason}` : ''}
                </code>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Kesegaran">
        <p className="tabular-nums">
          Diperiksa <TimeText iso={check.checked_at} />
        </p>
        <ul className="space-y-1">
          {check.sources.map((source) => {
            const label = cacheLabel(source)
            return (
              <li key={source.source} className="text-redup">
                <span className="text-teks">{sourceName(source.source)}</span>:{' '}
                {label === null
                  ? 'tidak tersedia'
                  : label === 'Cache'
                    ? <>Cache, berlaku sampai <TimeText iso={source.expires_at} /></>
                    : 'Ambil baru'}
              </li>
            )
          })}
        </ul>
      </Section>

      <Section title="Flag">
        {check.flags.length === 0 ? (
          <p className="text-redup">Tidak ada flag.</p>
        ) : (
          <ul className="space-y-2">
            {check.flags.map((flag) => (
              <li key={flag}>
                <FlagChip flag={flag} />
                <p className="mt-0.5 text-redup">{flagText(flag)}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Aksi">
        {canRun && (
          <div>
            <Button
              onClick={() => onRerun(check.ip)}
              disabled={submitting}
              className="w-full"
            >
              {submitting ? 'Memeriksa…' : 'Cek ulang'}
            </Button>
            <p className="mt-1 text-kecil text-redup">
              Memanggil pengecekan lagi. Sumber yang sudah ada di cache tidak diambil ulang.
            </p>
          </div>
        )}
        <CopyResult key={check.id} text={buildCopyText(check)} />
      </Section>

      {links.length > 0 && (
        <Section title="Buka di situs sumber">
          <ul className="space-y-1">
            {links.map((link) => (
              <li key={link.name}>
                <a
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-aksen underline underline-offset-2"
                >
                  {link.name}
                  <IconExternal className="size-3.5" />
                  <span className="sr-only">(tab baru)</span>
                </a>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="MISP">
        {simulated ? (
          <p>Hasil simulasi tidak boleh dikirim ke MISP.</p>
        ) : (
          <p className="text-redup">Pengiriman ke MISP tersedia pada tahap berikutnya.</p>
        )}
      </Section>
    </div>
  )
}
