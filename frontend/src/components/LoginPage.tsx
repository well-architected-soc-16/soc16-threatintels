import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/useAuth'
import type { LoginError } from '../auth/AuthContext'
import { Button } from './Button'
import { IconX } from './Icon'

// 401 tidak membedakan user tidak ada vs password salah (pesan umum, sama seperti backend).
const MESSAGES: Record<LoginError, string> = {
  bad_credentials: 'Username atau password salah',
  network:
    'API tidak terjangkau. Pastikan backend berjalan, lalu coba lagi.',
  unexpected: 'Login gagal. Coba lagi; bila berulang, hubungi admin.',
}

const FIELD =
  'w-full rounded-md border border-garis bg-tanah px-3 py-2 text-isi text-teks placeholder:text-redup disabled:opacity-60'

export function LoginPage() {
  const { login, notice } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Wajib paling awal: submit bawaan peramban akan menaruh isian form (termasuk password) di URL.
    event.preventDefault()
    if (pending) return
    setError(null)
    setPending(true)
    const result = await login(username, password)
    setPending(false)
    if (!result.ok) {
      setError(MESSAGES[result.error])
      setPassword('')
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <section className="w-full max-w-sm rounded-lg border border-garis/35 bg-panel p-6">
        <h1 className="text-judul font-semibold">SOC16 TI</h1>
        <p className="mt-1 text-padat text-redup">
          Masuk untuk memeriksa reputasi IP
        </p>

        {notice !== null && (
          <p
            role="status"
            className="mt-4 rounded-md border border-garis px-3 py-2 text-padat"
          >
            {notice}
          </p>
        )}

        <form
          method="post"
          onSubmit={handleSubmit}
          className="mt-5 space-y-4"
        >
          <div>
            <label htmlFor="username" className="mb-1 block text-padat text-redup">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              autoFocus
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={pending}
              className={FIELD}
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-padat text-redup">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={pending}
              className={FIELD}
            />
          </div>

          {error !== null && (
            <p
              role="alert"
              className="flex items-start gap-2 rounded-md border border-gagal px-3 py-2 text-padat text-gagal"
            >
              <IconX className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          <Button type="submit" disabled={pending} className="w-full">
            {pending ? 'Masuk…' : 'Masuk'}
          </Button>
        </form>
      </section>
    </main>
  )
}
