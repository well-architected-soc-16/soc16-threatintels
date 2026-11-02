import type { ReactNode } from 'react'
import { IconX } from './Icon'

// Chip netral: batas Garis, tanpa isi warna. Tidak memakai warna verdict (Keputusan 10).
export function Chip({
  children,
  mono = false,
}: {
  children: ReactNode
  mono?: boolean
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border border-garis px-2 py-0.5 text-padat text-teks ${mono ? 'font-mono' : ''}`}
    >
      {children}
    </span>
  )
}

// Status kegagalan: chip berbingkai tanpa isi + ikon X + teks (pengecualian Keputusan 10).
// Berbeda bentuk dari SANGAT_TINGGI, yang chip terisi.
export function FailureChip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-gagal px-2 py-0.5 text-padat text-gagal">
      <IconX className="size-3.5" />
      {children}
    </span>
  )
}
