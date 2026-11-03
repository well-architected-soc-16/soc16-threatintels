import { useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { TopBar, type View } from './TopBar'
import { useHealth } from './useHealth'

const PANEL = 'p-4'
const PANEL_TITLE = 'text-sub font-semibold'
const PLACEHOLDER = 'mt-2 text-padat text-redup'

// Urutan DOM sengaja mengikuti urutan visual desktop (riwayat, bukti, keputusan) supaya urutan Tab
// sama dengan urutan baca. Di bawah 1024px panel ditumpuk bukti → keputusan → riwayat lewat CSS `order`;
// konsekuensinya Tab di layar sempit lebih dulu melewati riwayat (layar sempit = sentuh, diterima).
export function Shell() {
  const { user, sessionEnd, api, logout, refreshUser } = useAuth()
  const [view, setView] = useState<View>('workbench')
  const health = useHealth(api, view)

  // Ganti tampilan = validasi ulang sesi. Token yang sudah tidak berlaku (kedaluwarsa, akun dinonaktifkan)
  // menghasilkan 401 dan otomatis mengembalikan ke login; tanpa ini shell kosong tidak pernah memanggil API.
  useEffect(() => {
    void refreshUser()
  }, [view, refreshUser])

  if (user === null) return null

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar
        user={user}
        sessionEnd={sessionEnd}
        health={health}
        view={view}
        onNavigate={setView}
        onLogout={logout}
      />

      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[232px_minmax(0,1fr)_264px] xl:grid-cols-[272px_minmax(0,1fr)_304px]">
        <aside
          aria-label="Riwayat"
          className={`${PANEL} order-3 border-t border-garis/35 bg-panel lg:order-none lg:sticky lg:top-14 lg:max-h-[calc(100vh-3.5rem)] lg:self-start lg:overflow-y-auto lg:border-t-0 lg:border-r`}
        >
          <h2 className={PANEL_TITLE}>Riwayat</h2>
          <p className={PLACEHOLDER}>Belum ada riwayat yang dimuat.</p>
        </aside>

        <main className={`${PANEL} order-1 lg:order-none`}>
          {view === 'workbench' ? (
            <>
              <h1 className="sr-only">Workbench investigasi IP</h1>
              <h2 className={PANEL_TITLE}>Bukti</h2>
              <p className={PLACEHOLDER}>Belum ada pengecekan yang dipilih.</p>
            </>
          ) : (
            <>
              <h1 className="text-judul font-semibold">Kiriman MISP</h1>
              <p className={PLACEHOLDER}>Daftar kiriman belum dimuat.</p>
            </>
          )}
        </main>

        <aside
          aria-label="Keputusan dan aksi"
          className={`${PANEL} order-2 border-t border-garis/35 bg-panel lg:order-none lg:sticky lg:top-14 lg:max-h-[calc(100vh-3.5rem)] lg:self-start lg:overflow-y-auto lg:border-t-0 lg:border-l`}
        >
          <h2 className={PANEL_TITLE}>Keputusan</h2>
          <p className={PLACEHOLDER}>Aksi muncul setelah ada hasil pengecekan.</p>
        </aside>
      </div>

      <footer className="border-t border-garis/35 bg-panel px-4 py-2 text-kecil text-redup">
        Sumber: AbuseIPDB, VirusTotal · Skor = label indikasi untuk triase,
        bukan peluang IP jahat.
      </footer>
    </div>
  )
}
