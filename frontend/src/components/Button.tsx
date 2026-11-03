import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary'

const BASE =
  'inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-isi font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60'

const VARIANTS: Record<Variant, string> = {
  // Aksen hanya untuk elemen interaktif (Keputusan 10).
  primary:
    'bg-aksen text-aksen-ink enabled:hover:brightness-110 enabled:active:brightness-95',
  secondary:
    'border border-garis text-teks enabled:hover:bg-panel enabled:active:bg-tanah',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

export function Button({
  variant = 'primary',
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${BASE} ${VARIANTS[variant]} ${className}`}
      {...rest}
    />
  )
}
