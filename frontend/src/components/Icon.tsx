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

export function IconCheck({ className = 'size-4' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3 8.5l3.2 3.2L13 4.8" />
    </svg>
  )
}

export function IconExternal({ className = 'size-4' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M7 3H3.5v9.5H13V9M9.5 3H13v3.5M13 3L7.5 8.5" />
    </svg>
  )
}
