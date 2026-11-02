// Ikon SVG buatan sendiri, satu gaya garis (2px, ujung bulat). Tanpa icon pack (Keputusan 2).
// Dekoratif: teks di sampingnya selalu membawa maknanya, jadi disembunyikan dari pembaca layar.

export function IconX({ className = 'size-4' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" />
    </svg>
  )
}
