import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { createApiClient } from '../api/client'
import type { UserOut } from '../api/types'
import { AuthContext, type AuthContextValue } from '../auth/AuthContext'
import { LoginPage } from './LoginPage'
import { Shell } from './Shell'

// Render markup di Node (tanpa peramban): memastikan komponen tidak crash dan mengunci atribut yang
// menyangkut keamanan/aksesibilitas. Efek (fetch /health, /auth/me) tidak berjalan di render statis.

const user = (role: UserOut['role'], over: Partial<UserOut> = {}): UserOut => ({
  id: 1,
  username: 'tester',
  role,
  can_send_misp: false,
  is_active: true,
  created_at: '2026-11-02T10:00:00+07:00',
  updated_at: '2026-11-02T10:00:00+07:00',
  ...over,
})

function context(over: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: null,
    sessionEnd: null,
    notice: null,
    api: createApiClient({
      getToken: () => null,
      onUnauthorized: () => {},
      fetchImpl: (() => Promise.reject(new TypeError('offline'))) as typeof fetch,
    }),
    login: () => Promise.resolve({ ok: true }),
    logout: () => {},
    refreshUser: () => Promise.resolve(),
    ...over,
  }
}

function render(node: React.ReactNode, value: AuthContextValue): string {
  return renderToStaticMarkup(
    <AuthContext.Provider value={value}>{node}</AuthContext.Provider>,
  )
}

describe('LoginPage', () => {
  const html = render(<LoginPage />, context())

  it('form memakai method=post (submit bawaan tidak pernah menaruh password di URL)', () => {
    expect(html).toMatch(/<form[^>]*method="post"/)
  })

  it('atribut autocomplete benar untuk pengelola password', () => {
    expect(html).toMatch(/<input[^>]*name="username"[^>]*autoComplete="username"|<input[^>]*autoComplete="username"[^>]*name="username"/i)
    expect(html).toMatch(/type="password"/)
    expect(html).toMatch(/autoComplete="current-password"/i)
  })

  it('tanpa notice dan tanpa galat saat pertama dibuka', () => {
    expect(html).not.toContain('role="status"')
    expect(html).not.toContain('role="alert"')
  })

  it('menampilkan notice sesi berakhir bila ada', () => {
    const withNotice = render(
      <LoginPage />,
      context({ notice: 'Sesi berakhir, login lagi' }),
    )
    expect(withNotice).toContain('role="status"')
    expect(withNotice).toContain('Sesi berakhir, login lagi')
  })

  it('tidak ada tautan ke CDN atau sumber eksternal', () => {
    expect(html).not.toMatch(/https?:\/\//)
  })
})

describe('Shell', () => {
  const htmlFor = (u: UserOut, sessionEnd: string | null = '14:33') =>
    render(<Shell />, context({ user: u, sessionEnd }))

  it('menampilkan nav, role, username, jam sesi, dan Keluar', () => {
    const html = htmlFor(user('viewer'))
    expect(html).toContain('Workbench')
    expect(html).toContain('Kiriman MISP')
    expect(html).toContain('tester')
    expect(html).toContain('viewer')
    expect(html).toContain('sesi berakhir')
    expect(html).toContain('14:33')
    expect(html).toContain('WIB')
    expect(html).toContain('Keluar')
  })

  it('rel menempel di bawah top bar yang tingginya diukur (--topbar-h), bukan angka keras 56px', () => {
    const html = htmlFor(user('admin'))
    expect(html.match(/sticky top-0 z-10/g)?.length).toBe(1)
    expect(html.match(/lg:top-\[var\(--topbar-h,5rem\)\]/g)?.length).toBe(2)
    expect(html.match(/lg:max-h-\[calc\(100vh-var\(--topbar-h,5rem\)\)\]/g)?.length).toBe(2)
    expect(html).not.toContain('lg:top-14')
    expect(html).not.toContain('3.5rem')
  })

  it('viewer tidak punya kolom pencarian; admin dan analyst punya', () => {
    expect(htmlFor(user('viewer'))).not.toContain('role="search"')
    expect(htmlFor(user('analyst'))).toContain('role="search"')
    expect(htmlFor(user('admin'))).toContain('role="search"')
  })

  it('tanpa exp terbaca, jam sesi tidak ditampilkan (tidak mengarang)', () => {
    expect(htmlFor(user('admin'), null)).not.toContain('sesi berakhir')
  })

  it('belum ada hasil /health: badge menunjukkan "…", bukan "sehat" yang dikarang', () => {
    const html = htmlFor(user('analyst'))
    expect(html).toContain('MISP: …')
    expect(html).not.toContain('MISP: mock')
  })

  it('urutan DOM = urutan visual desktop; layar sempit: bukti, keputusan, riwayat', () => {
    const html = htmlFor(user('admin'))
    const riwayat = html.indexOf('aria-label="Riwayat"')
    const bukti = html.indexOf('<main')
    const keputusan = html.indexOf('aria-label="Keputusan dan aksi"')
    expect(riwayat).toBeGreaterThan(-1)
    expect(riwayat).toBeLessThan(bukti)
    expect(bukti).toBeLessThan(keputusan)
    expect(html).toMatch(/<main[^>]*order-1/)
    expect(html).toMatch(/aria-label="Keputusan dan aksi"[^>]*order-2/)
    expect(html).toMatch(/aria-label="Riwayat"[^>]*order-3/)
  })

  it('landmark dan satu h1 per tampilan', () => {
    const html = htmlFor(user('admin'))
    expect(html).toContain('<header')
    expect(html).toContain('<footer')
    expect(html.match(/<h1/g)?.length).toBe(1)
  })

  it('footer memuat kalimat skor bukan probabilitas dan tanpa tanda persen pada skor', () => {
    const html = htmlFor(user('viewer'))
    expect(html).toContain('bukan peluang IP jahat')
    expect(html).not.toContain('%')
  })

  it('tidak merender apa pun bila user kosong', () => {
    expect(render(<Shell />, context({ user: null }))).toBe('')
  })
})
