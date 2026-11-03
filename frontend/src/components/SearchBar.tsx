import { useState, type FormEvent } from 'react'
import type { SubmitError } from '../workbench/store'
import { Button } from './Button'
import { IconX } from './Icon'

interface SearchBarProps {
  submitting: boolean
  error: SubmitError | null
  onSubmit: (ip: string) => Promise<boolean>
  onEdit: () => void
}

const FIELD =
  'w-full rounded-md border border-garis bg-tanah px-3 py-2 font-mono text-isi text-teks placeholder:font-sans placeholder:text-redup read-only:opacity-60'

// Validasi di browser hanya untuk "kosong"; validasi IP sebenarnya oleh backend (Tahap 2 butir 1).
export function SearchBar({ submitting, error, onSubmit, onEdit }: SearchBarProps) {
  const [value, setValue] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Pertama: submit bawaan peramban akan menaruh isian di URL.
    event.preventDefault()
    const ok = await onSubmit(value)
    if (ok) setValue('')
  }

  return (
    <div className="flex min-w-64 max-w-xl flex-1 flex-col">
      <form
        method="post"
        role="search"
        onSubmit={handleSubmit}
        className="flex gap-2"
      >
        <label htmlFor="ip-search" className="sr-only">
          Alamat IPv4 publik
        </label>
        <input
          id="ip-search"
          name="ip"
          type="text"
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          autoFocus
          value={value}
          // readOnly (bukan disabled) agar fokus keyboard tidak jatuh ke <body> saat pengecekan selesai.
          readOnly={submitting}
          aria-busy={submitting}
          aria-describedby="ip-search-status"
          placeholder="IPv4 publik, mis. 118.25.6.39"
          onChange={(event) => {
            setValue(event.target.value)
            onEdit()
          }}
          className={FIELD}
        />
        <Button type="submit" disabled={submitting} className="shrink-0">
          {submitting ? 'Memeriksa…' : 'Cek IP'}
        </Button>
      </form>

      <div id="ip-search-status" className="mt-1 min-h-5">
        {submitting ? (
          <p className="text-kecil text-redup">
            Memeriksa… bisa sampai belasan detik.
          </p>
        ) : error !== null ? (
          <p
            role="alert"
            className="flex items-start gap-1.5 rounded-md border border-gagal px-2 py-1 text-padat text-gagal"
          >
            <IconX className="mt-0.5 size-3.5 shrink-0" />
            <span>
              {error.message}
              {error.kind === 'input_ditolak' && (
                <>
                  {' '}
                  <code className="font-mono text-kecil">{error.reasonCode}</code>
                </>
              )}
            </span>
          </p>
        ) : (
          <p className="text-kecil text-redup">
            Satu IPv4 publik saja; IPv6 dan alamat privat ditolak.
          </p>
        )}
      </div>
    </div>
  )
}
