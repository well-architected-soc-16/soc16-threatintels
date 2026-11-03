import type { ReactNode } from 'react'
import type { UserOut } from '../api/types'
import type { HealthState } from '../lib/health'
import { Button } from './Button'
import { Chip, FailureChip } from './Chip'

export type View = 'workbench' | 'misp'

const NAV: { view: View; label: string }[] = [
  { view: 'workbench', label: 'Workbench' },
  { view: 'misp', label: 'Kiriman MISP' },
]

function HealthBadge({ health }: { health: HealthState | null }) {
  if (health === null) return <Chip>MISP: …</Chip>
  if (health.kind === 'unreachable') {
    return <FailureChip>API: tidak terjangkau</FailureChip>
  }
  if (health.kind === 'degraded') {
    return <FailureChip>API: DB error</FailureChip>
  }
  return <Chip>MISP: {health.mispMode}</Chip>
}

interface TopBarProps {
  user: UserOut
  sessionEnd: string | null
  health: HealthState | null
  view: View
  onNavigate: (view: View) => void
  onLogout: () => void
  // Kolom pencarian; null untuk akun tanpa hak membuat pengecekan (viewer).
  search?: ReactNode
}

export function TopBar({
  user,
  sessionEnd,
  health,
  view,
  onNavigate,
  onLogout,
  search = null,
}: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 flex min-h-14 flex-wrap items-center gap-x-6 gap-y-2 border-b border-garis/35 bg-panel px-4 py-2">
      <span className="text-sub font-semibold">SOC16 TI</span>

      {search}

      <nav aria-label="Tampilan" className="flex gap-1">
        {NAV.map(({ view: target, label }) => {
          const active = target === view
          return (
            <button
              key={target}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => onNavigate(target)}
              className={`border-b-2 px-3 py-1.5 text-isi transition-colors duration-150 ${
                active
                  ? 'border-aksen text-teks'
                  : 'border-transparent text-redup hover:text-teks'
              }`}
            >
              {label}
            </button>
          )
        })}
      </nav>

      <div className="ml-auto flex flex-wrap items-center gap-x-4 gap-y-2">
        <HealthBadge health={health} />
        <span className="flex items-center gap-2 text-padat">
          <span>{user.username}</span>
          <Chip>{user.role}</Chip>
        </span>
        {sessionEnd !== null && (
          <span className="tabular-nums text-padat text-redup">
            sesi berakhir {sessionEnd} WIB
          </span>
        )}
        <Button variant="secondary" onClick={onLogout}>
          Keluar
        </Button>
      </div>
    </header>
  )
}
