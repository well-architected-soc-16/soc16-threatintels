import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { canCheck, mispDeniedText } from '../lib/can'
import { useMisp } from '../workbench/useMisp'
import { useWorkbench } from '../workbench/useWorkbench'
import { DecisionRail } from './DecisionRail'
import { EvidencePanel } from './EvidencePanel'
import { HistoryRail } from './HistoryRail'
import { MispPanel } from './MispPanel'
import { MispView } from './MispView'
import { SearchBar } from './SearchBar'
import { TopBar, type View } from './TopBar'
import { useHealth } from './useHealth'
import { useCssVarHeight } from './useCssVarHeight'

const PANEL = 'p-4'

// Urutan DOM sengaja mengikuti urutan visual desktop (riwayat, bukti, keputusan) supaya urutan Tab
// sama dengan urutan baca. Di bawah 1024px panel ditumpuk bukti → keputusan → riwayat lewat CSS `order`;
// konsekuensinya Tab di layar sempit lebih dulu melewati riwayat (layar sempit = sentuh, diterima).
export function Shell() {
  const { user, sessionEnd, api, logout, refreshUser } = useAuth()
  const [view, setView] = useState<View>('workbench')
  const health = useHealth(api, view)
  const [state, store] = useWorkbench(api)
  const [misp, mispStore] = useMisp(api)
  const rootRef = useRef<HTMLDivElement>(null)
  const barRef = useRef<HTMLDivElement>(null)
  const footerRef = useRef<HTMLElement>(null)
  useCssVarHeight(rootRef, barRef, '--topbar-h')
  useCssVarHeight(rootRef, footerRef, '--footer-h')

  // Ganti tampilan = validasi ulang sesi. Token yang sudah tidak berlaku (kedaluwarsa, akun dinonaktifkan)
  // menghasilkan 401 dan otomatis mengembalikan ke login; tanpa ini shell kosong tidak pernah memanggil API.
  useEffect(() => {
    void refreshUser()
  }, [view, refreshUser])

  // Masuk ke tampilan Kiriman MISP = ambil kiriman terbaru dari pengguna lain.
  useEffect(() => {
    if (view === 'misp') void mispStore.refresh()
  }, [view, mispStore])

  if (user === null) return null

  // Hanya tampilan: kontrol sebenarnya ada di backend (403).
  const canRun = canCheck(user)

  return (
    <div ref={rootRef} className="flex min-h-screen flex-col">
      <div ref={barRef} className="sticky top-0 z-10">
        <TopBar
          user={user}
          sessionEnd={sessionEnd}
          health={health}
          view={view}
          onNavigate={setView}
          onLogout={logout}
          search={
            canRun ? (
              <SearchBar
                submitting={state.submitting}
                error={state.submitError}
                onSubmit={(ip) => {
                  // Hasil pengecekan tampil di tampilan Workbench.
                  setView('workbench')
                  return store.submit(ip)
                }}
                onEdit={store.clearSubmitError}
              />
            ) : null
          }
        />
      </div>

      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[232px_minmax(0,1fr)_264px] xl:grid-cols-[272px_minmax(0,1fr)_304px]">
        <aside
          aria-label="Riwayat"
          className={`${PANEL} order-3 border-t border-garis/35 bg-panel lg:order-none lg:sticky lg:top-[var(--topbar-h,5rem)] lg:max-h-[calc(100vh-var(--topbar-h,5rem)-var(--footer-h,2.5rem))] lg:self-start lg:overflow-y-auto lg:border-t-0 lg:border-r`}
        >
          <HistoryRail
            state={state}
            onSelect={(id) => {
              setView('workbench')
              void store.select(id)
            }}
            onLoadMore={() => void store.loadMore()}
            onRetry={() => void store.loadInitial()}
          />
        </aside>

        <main className={`${PANEL} order-1 lg:order-none`}>
          {view === 'workbench' ? (
            <EvidencePanel
              selected={state.selected}
              detailLoading={state.detailLoading}
              detailError={state.detailError}
              submitting={state.submitting}
              canRun={canRun}
            />
          ) : (
            <MispView
              state={misp}
              onLoadMore={() => void mispStore.loadMore()}
              onRefresh={() => void mispStore.refresh()}
              onOpenCheck={(id) => {
                setView('workbench')
                void store.select(id)
              }}
            />
          )}
        </main>

        <aside
          aria-label="Keputusan dan aksi"
          className={`${PANEL} order-2 border-t border-garis/35 bg-panel lg:order-none lg:sticky lg:top-[var(--topbar-h,5rem)] lg:max-h-[calc(100vh-var(--topbar-h,5rem)-var(--footer-h,2.5rem))] lg:self-start lg:overflow-y-auto lg:border-t-0 lg:border-l`}
        >
          <DecisionRail
            check={state.selected}
            canRun={canRun}
            submitting={state.submitting}
            onRerun={(ip) => {
              setView('workbench')
              void store.submit(ip)
            }}
            misp={
              state.selected === null ? undefined : (
                <MispPanel
                  check={state.selected}
                  misp={misp}
                  deniedText={mispDeniedText(user)}
                  onSubmit={mispStore.submit}
                  onClearIssue={mispStore.clearIssue}
                  onRetryLoad={() => void mispStore.loadInitial()}
                />
              )
            }
          />
        </aside>
      </div>

      <footer ref={footerRef} className="border-t border-garis/35 bg-panel px-4 py-2 text-kecil text-redup">
        Sumber: AbuseIPDB, VirusTotal
        {state.selected !== null && (
          <>
            {' '}
            · scoring_version <code className="font-mono">{state.selected.scoring_version}</code>
          </>
        )}{' '}
        · Skor = label indikasi untuk triase, bukan peluang IP jahat.
      </footer>
    </div>
  )
}
