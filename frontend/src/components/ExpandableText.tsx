import { useState } from 'react'

const LIMIT = 120

// Teks panjang dipotong dan bisa dibuka dengan tombol teks. Selalu dirender sebagai teks biasa (React escaping);
// whitespace-pre-wrap menjaga baris baru yang diketik analis.
export function ExpandableText({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  const chars = Array.from(text)
  if (chars.length <= LIMIT) {
    return <span className="whitespace-pre-wrap [overflow-wrap:anywhere]">{text}</span>
  }
  return (
    <span>
      <span className="whitespace-pre-wrap [overflow-wrap:anywhere]">
        {open ? text : `${chars.slice(0, LIMIT).join('')}…`}
      </span>{' '}
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="text-aksen underline underline-offset-2"
      >
        {open ? 'Ringkas' : 'Tampilkan semua'}
      </button>
    </span>
  )
}
